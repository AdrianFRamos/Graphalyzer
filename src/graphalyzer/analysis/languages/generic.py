"""Analisador genérico sobre tree-sitter.

Um só algoritmo serve todas as linguagens: o que muda entre elas está em
`specs.py`. A precisão é menor que a de um parser dedicado (não há resolução
de tipos nem de escopo), mas basta para o que o grafo mostra — quem chama
quem, e qual variável entra em qual função.

Tudo sai de um único parse por arquivo. Reanalisar o trecho recortado de uma
função depois gerava falso positivo: fora do contexto da classe, a própria
assinatura `metodo(a, b)` volta a parsear como chamada.
"""

import logging
from pathlib import Path
from typing import List, Optional

from graphalyzer.analysis.languages.base import (
    CallInfo,
    ClassInfo,
    FileInfo,
    FunctionInfo,
    ImportInfo,
    Parameter,
)
from graphalyzer.analysis.languages.specs import LanguageSpec

logger = logging.getLogger(__name__)

_PARSERS = {}

_TIPOS_DE_NOME = ("identifier", "type_identifier", "field_identifier", "simple_identifier")


def _parser(spec: LanguageSpec):
    """Parser da linguagem, criado uma vez (carregar gramática é caro)."""
    if spec.name not in _PARSERS:
        from tree_sitter_language_pack import get_parser

        _PARSERS[spec.name] = get_parser(spec.name)
    return _PARSERS[spec.name]


def _texto(node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _limpo(node) -> Optional[str]:
    """Texto de um nó de tipo, sem o `:` ou `->` que algumas gramáticas incluem."""
    if node is None:
        return None
    return _texto(node).lstrip(":").replace("->", "").strip() or None


def _nome(node, profundidade: int = 2) -> Optional[str]:
    """Nome declarado por um nó.

    Tenta o campo `name` (caminho confiável) e desce um pouco quando a
    gramática embrulha a declaração — em Go, por exemplo, o nome do struct
    fica em `type_declaration > type_spec > type_identifier`.
    """
    campo = node.child_by_field_name("name")
    if campo is not None:
        return _texto(campo)

    for filho in node.children:
        if filho.type in _TIPOS_DE_NOME:
            return _texto(filho)

    if profundidade > 0:
        for filho in node.children:
            if filho.is_named:
                achado = _nome(filho, profundidade - 1)
                if achado:
                    return achado

    return None


def _descer(node, tipos, parar_em=()):
    """Percorre a subárvore rendendo nós dos tipos pedidos.

    Não desce para dentro do que já casou nem para dentro de `parar_em`: sem
    isso, uma classe aninhada devolveria seus métodos para a classe de fora, e
    o `function_signature` interno do Dart duplicaria cada método.
    """
    for filho in node.children:
        if filho.type in tipos:
            yield filho
            continue
        if filho.type not in parar_em:
            yield from _descer(filho, tipos, parar_em)


class GenericAnalyzer:
    """Analisa qualquer linguagem descrita por um `LanguageSpec`."""

    def __init__(self, spec: LanguageSpec):
        self.spec = spec
        self.language = spec.name
        self.extensions = spec.extensions

    def parse_file(self, file_path: str) -> Optional[FileInfo]:
        try:
            source = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("Não foi possível ler %s: %s", file_path, exc)
            return None

        raiz = _parser(self.spec).parse(source.encode("utf-8")).root_node

        classes = self._classes(raiz, source)
        ja_usados = {(m.name, m.line_number) for c in classes for m in c.methods}

        functions = [
            f
            for f in (
                self._funcao(n, source)
                for n in _descer(
                    raiz,
                    self.spec.functions,
                    parar_em=self.spec.classes + self.spec.functions,
                )
                if _nome(n)
            )
            if (f.name, f.line_number) not in ja_usados
        ]

        return FileInfo(
            file_path=file_path,
            module_name=Path(file_path).stem,
            docstring=None,
            imports=self._imports(raiz),
            functions=functions,
            classes=classes,
            source_code=source,
            language=self.spec.name,
        )

    # Calls e complexidade já vêm prontos do parse
    def extract_calls(self, function: FunctionInfo) -> List[CallInfo]:
        return function.calls

    def complexity(self, function: FunctionInfo) -> int:
        return function.complexity

    # -- Extração ---------------------------------------------------------

    def _classes(self, raiz, source: str) -> List[ClassInfo]:
        classes = []

        for node in _descer(raiz, self.spec.classes, parar_em=self.spec.classes):
            nome = _nome(node)
            if not nome:
                continue

            metodos = [
                self._funcao(m, source, is_method=True)
                for m in _descer(node, self.spec.functions, parar_em=self.spec.functions)
                if _nome(m)
            ]

            classes.append(
                ClassInfo(
                    name=nome,
                    line_number=node.start_point[0] + 1,
                    docstring=self._doc(node),
                    source_code=_texto(node),
                    base_classes=self._bases(node),
                    methods=metodos,
                    is_private=nome.startswith(self.spec.private_prefix),
                )
            )

        return classes

    def _funcao(self, node, source: str, is_method: bool = False) -> FunctionInfo:
        nome = _nome(node) or "<anônima>"

        corpo = self._corpo(node)
        fim = corpo.end_byte if corpo is not None else node.end_byte
        texto = source[node.start_byte : fim]

        return FunctionInfo(
            name=nome,
            line_number=node.start_point[0] + 1,
            docstring=self._doc(node),
            source_code=texto,
            parameters=self._parametros(node),
            return_type=self._tipo_de_retorno(node),
            decorators=self._decoradores(node),
            is_async=any(f.type == "async" for f in node.children),
            is_method=is_method,
            is_private=nome.startswith(self.spec.private_prefix),
            calls=self._chamadas(corpo) if corpo is not None else [],
            complexity=self._complexidade(corpo) if corpo is not None else 1,
        )

    def _corpo(self, node):
        """O corpo da função — filho na maioria das linguagens, irmão no Dart."""
        campo = node.child_by_field_name("body")
        if campo is not None:
            return campo

        if self.spec.body_follows_signature:
            # No Dart o corpo segue a assinatura; num método, a assinatura está
            # embrulhada em `method_signature`, então subimos até achar o irmão
            atual = node
            while atual is not None:
                irmao = atual.next_sibling
                if irmao is not None and irmao.type in self.spec.bodies:
                    return irmao
                atual = atual.parent if atual.parent is not None else None
                if atual is not None and atual.type not in self.spec.functions:
                    break

        for filho in node.children:
            if filho.type in self.spec.bodies or filho.type == "block":
                return filho

        return None

    def _chamadas(self, corpo) -> List[CallInfo]:
        chamadas = []

        if self.spec.name == "dart":
            # Dart representa `somar(x)` como `identifier` + irmão `selector`
            for selector in _descer(corpo, ("selector", "argument_part")):
                texto = _texto(selector)
                if not texto.startswith("("):
                    continue
                anterior = selector.prev_sibling
                if anterior is None or anterior.type not in _TIPOS_DE_NOME:
                    continue
                chamadas.append(
                    CallInfo(
                        callee=_texto(anterior),
                        line_number=selector.start_point[0] + 1,
                        arguments=self._argumentos(selector),
                    )
                )
            return chamadas

        for node in _descer(corpo, self.spec.calls):
            nome = self._nome_da_chamada(node)
            if nome:
                chamadas.append(
                    CallInfo(
                        callee=nome,
                        line_number=node.start_point[0] + 1,
                        arguments=self._argumentos(node),
                    )
                )

        return chamadas

    def _complexidade(self, corpo) -> int:
        return 1 + sum(1 for _ in _descer(corpo, self.spec.branches))

    def _parametros(self, node) -> List[Parameter]:
        # Campo `parameters` primeiro: em Go, `method_declaration` tem também
        # um `parameter_list` para o receiver, que vem antes e não é parâmetro.
        lista = node.child_by_field_name("parameters")
        if lista is None:
            lista = next(iter(_descer(node, self.spec.parameter_lists)), None)
        if lista is None:
            return []

        parametros: List[Parameter] = []
        for p in lista.children:
            if p.type not in self.spec.parameters:
                continue

            nome_node = self._no_do_nome(p)
            nome = _texto(nome_node) if nome_node is not None else None
            if not nome:
                continue

            padrao = p.child_by_field_name("value") or p.child_by_field_name(
                "default_value"
            )
            parametros.append((nome, self._tipo_do_parametro(p, nome_node), _limpo(padrao)))

        return parametros

    def _no_do_nome(self, p):
        """O identificador que nomeia o parâmetro."""
        campo = p.child_by_field_name("name") or p.child_by_field_name("pattern")
        if campo is not None:
            return campo
        if p.type in _TIPOS_DE_NOME:
            return p
        # O nome é o último identificador simples (o resto é tipo)
        candidatos = [f for f in p.children if f.type in _TIPOS_DE_NOME]
        return candidatos[-1] if candidatos else None

    def _tipo_do_parametro(self, p, nome_node) -> Optional[str]:
        campo = p.child_by_field_name("type")
        if campo is not None:
            return _limpo(campo)

        if nome_node is None or nome_node is p:
            return None

        # O tipo é tudo menos o nome — funciona tanto para `int x` (tipo antes)
        # quanto para `x: int` e `itens []Item` (tipo depois)
        texto = _texto(p)
        inicio = nome_node.start_byte - p.start_byte
        fim = nome_node.end_byte - p.start_byte
        restante = (texto[:inicio] + " " + texto[fim:]).strip()
        return restante.lstrip(":").strip() or None

    def _tipo_de_retorno(self, node) -> Optional[str]:
        # Dart embrulha: `method_signature > function_signature`. Sem desembrulhar,
        # nenhum campo é encontrado e todo método fica sem tipo de retorno.
        interno = next(
            (f for f in node.children if f.type in self.spec.functions), None
        )
        if interno is not None:
            node = interno

        for campo in ("return_type", "result", "type"):
            alvo = node.child_by_field_name(campo)
            if alvo is not None:
                return _limpo(alvo)

        # Dart, Java, C: o tipo antecede o nome da função
        nome_node = node.child_by_field_name("name")
        if nome_node is None:
            nome_node = next((f for f in node.children if f.type in _TIPOS_DE_NOME), None)
        if nome_node is None:
            return None

        anteriores = [
            f
            for f in node.children
            if f.is_named and f.end_byte <= nome_node.start_byte
        ]
        if not anteriores:
            return None

        # Junta sem espaço antes de argumentos genéricos: no Dart, `Future` e
        # `<Map<String, dynamic>>` são nós irmãos e sairiam como "Future <Map…>".
        partes = [_texto(f) for f in anteriores if f.type not in ("modifiers",)]
        tipo = ""
        for parte in partes:
            if tipo and not parte.startswith(("<", "[", "?")):
                tipo += " "
            tipo += parte

        return tipo.strip() or None

    def _bases(self, node) -> List[str]:
        bases = []
        for campo in ("superclass", "interfaces", "superclasses", "trait"):
            alvo = node.child_by_field_name(campo)
            if alvo is not None:
                bases.extend(_texto(i) for i in _descer(alvo, _TIPOS_DE_NOME))
        return bases

    def _decoradores(self, node) -> List[str]:
        tipos = ("annotation", "decorator", "marker_annotation", "attribute_item")
        return [_texto(d).lstrip("@") for d in node.children if d.type in tipos]

    def _doc(self, node) -> Optional[str]:
        """Comentário imediatamente acima da declaração."""
        anterior = node.prev_sibling
        if (
            anterior is not None
            and anterior.type in self.spec.comments
            and node.start_point[0] - anterior.end_point[0] <= 1
        ):
            return _texto(anterior).strip()
        return None

    def _imports(self, raiz) -> List[ImportInfo]:
        imports = []
        for node in _descer(raiz, self.spec.imports):
            caminho = self._caminho_do_import(node)
            if caminho:
                imports.append(
                    ImportInfo(
                        module=caminho,
                        line_number=node.start_point[0] + 1,
                        is_from_import=True,
                        path=caminho,
                    )
                )
        return imports

    def _caminho_do_import(self, node) -> Optional[str]:
        fonte = node.child_by_field_name("source") or node.child_by_field_name("path")
        if fonte is not None:
            return _texto(fonte).strip("\"'<>")

        literais = ("string_literal", "string", "interpreted_string_literal",
                    "uri", "system_lib_string")
        for filho in _descer(node, literais):
            return _texto(filho).strip("\"'<>")

        pontilhados = ("scoped_identifier", "qualified_name", "namespace_name",
                       "identifier", "dotted_name")
        for filho in _descer(node, pontilhados):
            return _texto(filho)

        return None

    def _nome_da_chamada(self, node) -> Optional[str]:
        alvo = (
            node.child_by_field_name("function")
            or node.child_by_field_name("name")
            or node.child_by_field_name("constructor")
            or node
        )

        # `obj.metodo(...)` -> `metodo`: é o nome que o grafo consegue resolver
        nome = _texto(alvo).split("(")[0].strip().split(".")[-1].split("::")[-1]
        return nome if nome.isidentifier() else None

    def _argumentos(self, node) -> List[str]:
        args = node.child_by_field_name("arguments") or node

        # Os identificadores podem estar um ou dois níveis abaixo (no Dart,
        # dentro de `argument_part > arguments`), então a busca desce.
        nomes = [
            _texto(a)
            for a in _descer(args, _TIPOS_DE_NOME + ("field_expression",))
            if _texto(a).isidentifier()
        ]

        # Preserva a ordem e remove repetição, que quebraria o índice do
        # parâmetro correspondente no fluxo de dados
        vistos = set()
        return [n for n in nomes if not (n in vistos or vistos.add(n))]

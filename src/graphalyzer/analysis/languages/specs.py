"""Especificações por linguagem para o analisador tree-sitter.

Cada gramática nomeia seus nós de um jeito — Go tem `method_declaration`,
Dart tem `method_signature`, JS tem `method_definition`. Em vez de uma classe
por linguagem, tudo é declarado aqui: acrescentar uma linguagem é acrescentar
uma entrada, não escrever um analisador novo.

Os nomes abaixo foram lidos das gramáticas reais, não presumidos.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class LanguageSpec:
    """Como encontrar as construções de interesse numa gramática."""

    name: str  # nome no tree-sitter-language-pack
    label: str  # nome legível
    extensions: Tuple[str, ...]

    functions: Tuple[str, ...]  # declaram função ou método
    classes: Tuple[str, ...]  # declaram classe, struct, interface
    imports: Tuple[str, ...]
    calls: Tuple[str, ...]
    parameter_lists: Tuple[str, ...]
    parameters: Tuple[str, ...]

    # Dart e C++ separam assinatura e corpo em nós irmãos: sem juntar os dois,
    # o "código" da função sai sem corpo e nenhuma chamada é encontrada.
    body_follows_signature: bool = False
    bodies: Tuple[str, ...] = ()

    # Nós que somam +1 na complexidade ciclomática
    branches: Tuple[str, ...] = (
        "if_statement",
        "for_statement",
        "while_statement",
        "case_statement",
        "catch_clause",
        "conditional_expression",
        "do_statement",
        "switch_statement",
    )

    comments: Tuple[str, ...] = ("comment", "documentation_comment", "line_comment")
    private_prefix: str = "_"

    # Linguagens em que arquivos do mesmo pacote/namespace se enxergam sem
    # import explícito. Sem isto, nenhuma chamada entre arquivos do mesmo
    # pacote Go ou Java seria resolvida.
    package_scope: bool = False


_COMUNS = dict(
    parameter_lists=("formal_parameters", "parameters", "parameter_list"),
    parameters=("identifier", "required_parameter", "optional_parameter"),
)

SPECS: Dict[str, LanguageSpec] = {
    "dart": LanguageSpec(
        name="dart",
        label="Dart",
        extensions=(".dart",),
        functions=("function_signature", "method_signature", "constructor_signature"),
        classes=("class_definition", "mixin_declaration", "extension_declaration"),
        imports=("import_or_export",),
        calls=("selector",),
        parameter_lists=("formal_parameter_list",),
        parameters=("formal_parameter",),
        body_follows_signature=True,
        bodies=("function_body",),
        comments=("comment", "documentation_comment"),
    ),
    "javascript": LanguageSpec(
        name="javascript",
        label="JavaScript",
        extensions=(".js", ".jsx", ".mjs", ".cjs"),
        functions=(
            "function_declaration",
            "method_definition",
            "generator_function_declaration",
        ),
        classes=("class_declaration",),
        imports=("import_statement",),
        calls=("call_expression", "new_expression"),
        **_COMUNS,
    ),
    "typescript": LanguageSpec(
        name="typescript",
        label="TypeScript",
        extensions=(".ts", ".mts", ".cts"),
        functions=(
            "function_declaration",
            "method_definition",
            "method_signature",
            "function_signature",
        ),
        classes=("class_declaration", "interface_declaration", "type_alias_declaration"),
        imports=("import_statement",),
        calls=("call_expression", "new_expression"),
        **_COMUNS,
    ),
    "tsx": LanguageSpec(
        name="tsx",
        label="TypeScript (TSX)",
        extensions=(".tsx",),
        functions=("function_declaration", "method_definition", "method_signature"),
        classes=("class_declaration", "interface_declaration"),
        imports=("import_statement",),
        calls=("call_expression", "new_expression"),
        **_COMUNS,
    ),
    "go": LanguageSpec(
        name="go",
        package_scope=True,
        label="Go",
        extensions=(".go",),
        functions=("function_declaration", "method_declaration"),
        classes=("type_declaration",),  # o nome fica em type_spec, um nível abaixo
        imports=("import_declaration",),
        calls=("call_expression",),
        parameter_lists=("parameter_list",),
        parameters=("parameter_declaration",),
        branches=(
            "if_statement",
            "for_statement",
            "expression_switch_statement",
            "type_switch_statement",
            "select_statement",
            "communication_case",
            "expression_case",
        ),
    ),
    "java": LanguageSpec(
        name="java",
        package_scope=True,
        label="Java",
        extensions=(".java",),
        functions=("method_declaration", "constructor_declaration"),
        classes=("class_declaration", "interface_declaration", "enum_declaration"),
        imports=("import_declaration",),
        calls=("method_invocation", "object_creation_expression"),
        parameter_lists=("formal_parameters",),
        parameters=("formal_parameter", "spread_parameter"),
    ),
    "kotlin": LanguageSpec(
        name="kotlin",
        package_scope=True,
        label="Kotlin",
        extensions=(".kt", ".kts"),
        functions=("function_declaration",),
        classes=("class_declaration", "object_declaration"),
        imports=("import_header",),
        calls=("call_expression",),
        parameter_lists=("function_value_parameters",),
        parameters=("parameter",),
    ),
    "rust": LanguageSpec(
        name="rust",
        label="Rust",
        extensions=(".rs",),
        functions=("function_item",),
        classes=("struct_item", "enum_item", "trait_item", "impl_item"),
        imports=("use_declaration",),
        calls=("call_expression", "macro_invocation"),
        parameter_lists=("parameters",),
        parameters=("parameter",),
        branches=(
            "if_expression",
            "for_expression",
            "while_expression",
            "loop_expression",
            "match_arm",
        ),
        comments=("line_comment", "block_comment"),
    ),
    "csharp": LanguageSpec(
        name="csharp",
        package_scope=True,
        label="C#",
        extensions=(".cs",),
        functions=("method_declaration", "constructor_declaration"),
        classes=("class_declaration", "interface_declaration", "struct_declaration"),
        imports=("using_directive",),
        calls=("invocation_expression", "object_creation_expression"),
        parameter_lists=("parameter_list",),
        parameters=("parameter",),
    ),
    "ruby": LanguageSpec(
        name="ruby",
        label="Ruby",
        extensions=(".rb",),
        functions=("method", "singleton_method"),
        classes=("class", "module"),
        imports=("call",),
        calls=("call",),
        parameter_lists=("method_parameters",),
        parameters=("identifier", "optional_parameter"),
    ),
    "php": LanguageSpec(
        name="php",
        label="PHP",
        extensions=(".php",),
        functions=("function_definition", "method_declaration"),
        classes=("class_declaration", "interface_declaration", "trait_declaration"),
        imports=("namespace_use_declaration",),
        calls=("function_call_expression", "member_call_expression"),
        parameter_lists=("formal_parameters",),
        parameters=("simple_parameter", "property_promotion_parameter"),
    ),
    "swift": LanguageSpec(
        name="swift",
        label="Swift",
        extensions=(".swift",),
        functions=("function_declaration",),
        classes=("class_declaration", "protocol_declaration"),
        imports=("import_declaration",),
        calls=("call_expression",),
        parameter_lists=("parameter_list",),
        parameters=("parameter",),
    ),
    "c": LanguageSpec(
        name="c",
        package_scope=True,
        label="C",
        extensions=(".c", ".h"),
        functions=("function_definition",),
        classes=("struct_specifier", "union_specifier", "enum_specifier"),
        imports=("preproc_include",),
        calls=("call_expression",),
        parameter_lists=("parameter_list",),
        parameters=("parameter_declaration",),
        comments=("comment",),
    ),
    "cpp": LanguageSpec(
        name="cpp",
        package_scope=True,
        label="C++",
        extensions=(".cpp", ".cc", ".cxx", ".hpp", ".hh"),
        functions=("function_definition",),
        classes=("class_specifier", "struct_specifier"),
        imports=("preproc_include",),
        calls=("call_expression",),
        parameter_lists=("parameter_list",),
        parameters=("parameter_declaration",),
        comments=("comment",),
    ),
}

# extensão -> spec
EXTENSION_MAP: Dict[str, LanguageSpec] = {
    extension: spec for spec in SPECS.values() for extension in spec.extensions
}

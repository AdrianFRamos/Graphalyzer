"""
Interface abstrata para análise semântica com IA.
Suporta múltiplos provedores (Claude, GPT, etc) e preparado para modelo próprio.
"""

import logging

from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Resultado da análise semântica."""
    summary: str  # Resumo do que a função/classe faz
    category: str  # Categoria (ex: "utility", "core", "api", "test")
    key_points: List[str]  # Pontos-chave
    potential_issues: List[str]  # Possíveis problemas
    suggestions: List[str]  # Sugestões de melhoria
    confidence: float  # Confiança da análise (0-1)
    metadata: Dict[str, Any] = None


class AIAnalyzer(ABC):
    """Interface abstrata para analisadores de IA."""

    @abstractmethod
    def analyze_function(
        self,
        function_name: str,
        source_code: str,
        docstring: Optional[str] = None,
        context: Optional[str] = None,
    ) -> AnalysisResult:
        """Analisa uma função."""
        pass

    @abstractmethod
    def analyze_class(
        self,
        class_name: str,
        source_code: str,
        docstring: Optional[str] = None,
        context: Optional[str] = None,
    ) -> AnalysisResult:
        """Analisa uma classe."""
        pass

    @abstractmethod
    def generate_documentation(
        self,
        name: str,
        source_code: str,
        analysis: AnalysisResult,
    ) -> str:
        """Gera documentação para uma função/classe."""
        pass

    @abstractmethod
    def batch_analyze(
        self,
        items: List[Dict[str, Any]],
    ) -> List[AnalysisResult]:
        """Analisa múltiplos itens em lote."""
        pass


class MockAIAnalyzer(AIAnalyzer):
    """Analisador mock para testes (sem chamar LLM)."""

    def analyze_function(
        self,
        function_name: str,
        source_code: str,
        docstring: Optional[str] = None,
        context: Optional[str] = None,
    ) -> AnalysisResult:
        """Análise mock de função."""
        return AnalysisResult(
            summary=f"Mock analysis of function {function_name}",
            category="utility",
            key_points=["Mock point 1", "Mock point 2"],
            potential_issues=[],
            suggestions=["Add type hints", "Add docstring"],
            confidence=0.5,
        )

    def analyze_class(
        self,
        class_name: str,
        source_code: str,
        docstring: Optional[str] = None,
        context: Optional[str] = None,
    ) -> AnalysisResult:
        """Análise mock de classe."""
        return AnalysisResult(
            summary=f"Mock analysis of class {class_name}",
            category="core",
            key_points=["Mock point 1"],
            potential_issues=[],
            suggestions=["Add docstring"],
            confidence=0.5,
        )

    def generate_documentation(
        self,
        name: str,
        source_code: str,
        analysis: AnalysisResult,
    ) -> str:
        """Gera documentação mock."""
        return f"# {name}\n\n{analysis.summary}\n\n## Suggestions\n" + "\n".join(
            f"- {s}" for s in analysis.suggestions
        )

    def batch_analyze(
        self,
        items: List[Dict[str, Any]],
    ) -> List[AnalysisResult]:
        """Análise mock em lote."""
        return [
            self.analyze_function(
                item.get("name", "unknown"),
                item.get("source_code", ""),
            )
            for item in items
        ]


class LLMAnalyzer(AIAnalyzer):
    """Analisador usando LLM (Claude, GPT, etc)."""

    def __init__(self, provider: str = "claude", model: str = "claude-sonnet-5"):
        """Inicializa analisador LLM."""
        self.provider = provider
        self.model = model
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Inicializa cliente do LLM."""
        if self.provider == "claude":
            try:
                from anthropic import Anthropic
                self.client = Anthropic()
            except ImportError:
                logger.warning("Aviso: anthropic não instalado. Use: pip install anthropic")
        elif self.provider == "openai":
            try:
                from openai import OpenAI
                self.client = OpenAI()
            except ImportError:
                logger.warning("Aviso: openai não instalado. Use: pip install openai")

    def analyze_function(
        self,
        function_name: str,
        source_code: str,
        docstring: Optional[str] = None,
        context: Optional[str] = None,
    ) -> AnalysisResult:
        """Analisa uma função com LLM."""
        if not self.client:
            return self._fallback_analysis(function_name)

        prompt = self._build_analysis_prompt(
            "function",
            function_name,
            source_code,
            docstring,
            context,
        )

        return self._call_llm(prompt, "function")

    def analyze_class(
        self,
        class_name: str,
        source_code: str,
        docstring: Optional[str] = None,
        context: Optional[str] = None,
    ) -> AnalysisResult:
        """Analisa uma classe com LLM."""
        if not self.client:
            return self._fallback_analysis(class_name)

        prompt = self._build_analysis_prompt(
            "class",
            class_name,
            source_code,
            docstring,
            context,
        )

        return self._call_llm(prompt, "class")

    def generate_documentation(
        self,
        name: str,
        source_code: str,
        analysis: AnalysisResult,
    ) -> str:
        """Gera documentação com LLM."""
        if not self.client:
            return f"# {name}\n\n{analysis.summary}"

        prompt = f"""
Gere documentação profissional para:

Nome: {name}
Código:
```python
{source_code}
```

Análise: {analysis.summary}

Formato esperado:
# {name}

## Descrição
[descrição detalhada]

## Parâmetros
[lista de parâmetros]

## Retorno
[tipo e descrição do retorno]

## Exemplos
[exemplos de uso]

## Notas
[notas adicionais]
"""

        try:
            if self.provider == "claude":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Erro ao gerar documentação: {e}")
            return f"# {name}\n\n{analysis.summary}"

    def batch_analyze(
        self,
        items: List[Dict[str, Any]],
    ) -> List[AnalysisResult]:
        """Analisa múltiplos itens em lote."""
        results = []
        for item in items:
            if item.get("type") == "function":
                result = self.analyze_function(
                    item.get("name", "unknown"),
                    item.get("source_code", ""),
                    item.get("docstring"),
                )
            else:
                result = self.analyze_class(
                    item.get("name", "unknown"),
                    item.get("source_code", ""),
                    item.get("docstring"),
                )
            results.append(result)
        return results

    def _build_analysis_prompt(
        self,
        item_type: str,
        name: str,
        source_code: str,
        docstring: Optional[str],
        context: Optional[str],
    ) -> str:
        """Constrói prompt para análise."""
        prompt = f"""
Analise o seguinte código Python ({item_type}):

Nome: {name}
Código:
```python
{source_code}
```
"""
        if docstring:
            prompt += f"\nDocstring:\n{docstring}\n"

        if context:
            prompt += f"\nContexto:\n{context}\n"

        prompt += """
Por favor, forneça uma análise em JSON com os seguintes campos:
{
  "summary": "resumo do que faz (1-2 linhas)",
  "category": "categoria (utility/core/api/test/other)",
  "key_points": ["ponto 1", "ponto 2", ...],
  "potential_issues": ["problema 1", ...],
  "suggestions": ["sugestão 1", ...],
  "confidence": 0.85
}

Retorne APENAS o JSON, sem explicações adicionais.
"""
        return prompt

    def _call_llm(self, prompt: str, item_type: str) -> AnalysisResult:
        """Chama LLM e processa resposta."""
        try:
            if self.provider == "claude":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = response.content[0].text
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                )
                response_text = response.choices[0].message.content

            # Parse JSON da resposta
            import json
            import re
            
            # Extrair JSON da resposta
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return AnalysisResult(
                    summary=data.get("summary", ""),
                    category=data.get("category", "other"),
                    key_points=data.get("key_points", []),
                    potential_issues=data.get("potential_issues", []),
                    suggestions=data.get("suggestions", []),
                    confidence=data.get("confidence", 0.5),
                )
        except Exception as e:
            logger.error(f"Erro ao chamar LLM: {e}")

        return self._fallback_analysis("unknown")

    def _fallback_analysis(self, name: str) -> AnalysisResult:
        """Retorna análise padrão em caso de erro."""
        return AnalysisResult(
            summary=f"Analysis of {name}",
            category="other",
            key_points=[],
            potential_issues=[],
            suggestions=["Add docstring", "Add type hints"],
            confidence=0.0,
        )

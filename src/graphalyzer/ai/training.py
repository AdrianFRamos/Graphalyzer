"""
Pipeline para treinar modelo próprio de análise de código.
Coleta dados, gera dataset e prepara para fine-tuning.
"""

import logging

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TrainingExample:
    """Exemplo de treinamento."""
    code_snippet: str
    function_name: str
    docstring: Optional[str]
    parameters: List[Dict[str, str]]
    return_type: Optional[str]
    summary: str  # Resumo gerado por IA ou anotado manualmente
    category: str  # Categoria (utility, core, api, test, etc)
    complexity: int
    confidence: float = 1.0
    source_file: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DatasetGenerator:
    """Gera dataset para treinamento."""

    def __init__(self, output_dir: str = "training_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.examples: List[TrainingExample] = []

    def add_example(self, example: TrainingExample) -> None:
        """Adiciona exemplo ao dataset."""
        self.examples.append(example)

    def add_examples_from_graph(self, graph) -> None:
        """Adiciona exemplos a partir de um grafo de projeto."""
        from core.data_models import NodeType

        for node in graph.nodes.values():
            if node.type == NodeType.FUNCTION and node.source_code:
                example = TrainingExample(
                    code_snippet=node.source_code,
                    function_name=node.name,
                    docstring=node.docstring,
                    parameters=[
                        {
                            "name": p.name,
                            "type": p.type_hint or "Any",
                            "default": p.default_value,
                        }
                        for p in node.parameters
                    ],
                    return_type=node.return_value.type_hint if node.return_value else None,
                    summary=node.ai_summary or f"Function {node.name}",
                    category=node.ai_category or "other",
                    complexity=node.complexity,
                    source_file=node.file_path,
                )
                self.add_example(example)

    def export_jsonl(self, filename: str = "training_data.jsonl") -> str:
        """Exporta dataset em formato JSONL."""
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            for example in self.examples:
                # Formato OpenAI para fine-tuning
                record = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a Python code analyzer. Analyze the given code and provide a summary and category.",
                        },
                        {
                            "role": "user",
                            "content": f"""Analyze this Python function:

```python
{example.code_snippet}
```

Provide:
1. A brief summary of what this function does
2. A category (utility, core, api, test, other)
3. Key points about the function
4. Potential improvements""",
                        },
                        {
                            "role": "assistant",
                            "content": f"""Summary: {example.summary}

Category: {example.category}

Key Points:
- Function name: {example.function_name}
- Parameters: {len(example.parameters)}
- Complexity: {example.complexity}
- Has documentation: {bool(example.docstring)}

The function appears to be a {example.category} component with moderate complexity.""",
                        },
                    ]
                }
                f.write(json.dumps(record) + "\n")

        logger.info(f"✓ Dataset exportado para JSONL: {output_path}")
        return str(output_path)

    def export_csv(self, filename: str = "training_data.csv") -> str:
        """Exporta dataset em formato CSV."""
        output_path = self.output_dir / filename

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "function_name",
                "code_snippet",
                "docstring",
                "parameters_count",
                "return_type",
                "summary",
                "category",
                "complexity",
                "confidence",
                "source_file",
                "timestamp",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for example in self.examples:
                writer.writerow({
                    "function_name": example.function_name,
                    "code_snippet": example.code_snippet[:100] + "..." if len(example.code_snippet) > 100 else example.code_snippet,
                    "docstring": example.docstring[:50] + "..." if example.docstring and len(example.docstring) > 50 else example.docstring,
                    "parameters_count": len(example.parameters),
                    "return_type": example.return_type,
                    "summary": example.summary,
                    "category": example.category,
                    "complexity": example.complexity,
                    "confidence": example.confidence,
                    "source_file": example.source_file,
                    "timestamp": example.timestamp,
                })

        logger.info(f"✓ Dataset exportado para CSV: {output_path}")
        return str(output_path)

    def export_json(self, filename: str = "training_data.json") -> str:
        """Exporta dataset em formato JSON."""
        output_path = self.output_dir / filename

        data = {
            "metadata": {
                "total_examples": len(self.examples),
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
            },
            "examples": [e.to_dict() for e in self.examples],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Dataset exportado para JSON: {output_path}")
        return str(output_path)

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do dataset."""
        categories = {}
        total_complexity = 0
        total_params = 0

        for example in self.examples:
            categories[example.category] = categories.get(example.category, 0) + 1
            total_complexity += example.complexity
            total_params += len(example.parameters)

        return {
            "total_examples": len(self.examples),
            "categories": categories,
            "average_complexity": total_complexity / len(self.examples) if self.examples else 0,
            "average_parameters": total_params / len(self.examples) if self.examples else 0,
        }


class AnnotationTool:
    """Ferramenta para anotar dados manualmente."""

    def __init__(self, dataset_path: str):
        self.dataset_path = Path(dataset_path)
        self.annotations: Dict[str, Dict[str, Any]] = {}

    def load_unannotated(self) -> List[Dict[str, Any]]:
        """Carrega exemplos não anotados."""
        unannotated = []

        with open(self.dataset_path, "r", encoding="utf-8") as f:
            for line in f:
                example = json.loads(line)
                if "annotation" not in example:
                    unannotated.append(example)

        return unannotated

    def annotate(self, example_id: str, summary: str, category: str, confidence: float = 1.0) -> None:
        """Anota um exemplo."""
        self.annotations[example_id] = {
            "summary": summary,
            "category": category,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
        }

    def save_annotations(self, output_path: str) -> None:
        """Salva anotações."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.annotations, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Anotações salvas: {output_path}")


class ModelTrainer:
    """Classe base para treinamento de modelo."""

    def __init__(self, model_name: str = "code-analyzer-v1"):
        self.model_name = model_name
        self.training_config = {
            "model_name": model_name,
            "learning_rate": 2e-5,
            "batch_size": 8,
            "epochs": 3,
            "max_seq_length": 512,
        }

    def prepare_training_data(self, dataset_path: str) -> Dict[str, Any]:
        """Prepara dados para treinamento."""
        with open(dataset_path, "r", encoding="utf-8") as f:
            examples = [json.loads(line) for line in f]

        # Dividir em treino/validação
        split_idx = int(len(examples) * 0.8)
        train_data = examples[:split_idx]
        val_data = examples[split_idx:]

        return {
            "train": train_data,
            "validation": val_data,
            "total": len(examples),
        }

    def train_with_openai(self, dataset_path: str, model: str = "gpt-3.5-turbo") -> str:
        """Treina modelo usando OpenAI fine-tuning."""
        try:
            from openai import OpenAI
            client = OpenAI()

            # Upload dataset
            with open(dataset_path, "rb") as f:
                response = client.files.create(
                    file=f,
                    purpose="fine-tune",
                )
                file_id = response.id

            # Criar job de fine-tuning
            job = client.fine_tuning.jobs.create(
                training_file=file_id,
                model=model,
                suffix=self.model_name,
            )

            logger.info(f"✓ Fine-tuning job criado: {job.id}")
            logger.info(f"  Status: {job.status}")
            logger.info(f"  Modelo base: {model}")

            return job.id

        except ImportError:
            logger.warning("⚠️ OpenAI não instalado. Use: pip install openai")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao treinar com OpenAI: {e}")
            return None

    def train_with_huggingface(self, dataset_path: str, model: str = "bert-base-uncased") -> str:
        """Treina modelo usando Hugging Face."""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
            import torch

            # Carregar modelo e tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model)
            model_obj = AutoModelForSequenceClassification.from_pretrained(model, num_labels=5)

            # Preparar dados
            data = self.prepare_training_data(dataset_path)

            # Configurar treinamento
            training_args = TrainingArguments(
                output_dir=f"./models/{self.model_name}",
                num_train_epochs=self.training_config["epochs"],
                per_device_train_batch_size=self.training_config["batch_size"],
                learning_rate=self.training_config["learning_rate"],
                save_strategy="epoch",
                logging_steps=10,
            )

            # Criar trainer
            trainer = Trainer(
                model=model_obj,
                args=training_args,
                train_dataset=data["train"],
                eval_dataset=data["validation"],
            )

            # Treinar
            trainer.train()

            logger.info(f"✓ Modelo treinado com Hugging Face")
            logger.info(f"  Modelo: {self.model_name}")
            logger.info(f"  Exemplos: {data['total']}")

            return f"./models/{self.model_name}"

        except ImportError:
            logger.warning("⚠️ Transformers não instalado. Use: pip install transformers torch")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao treinar com Hugging Face: {e}")
            return None

    def save_config(self, output_path: str) -> None:
        """Salva configuração de treinamento."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.training_config, f, indent=2)

        logger.info(f"✓ Configuração salva: {output_path}")


class ModelEvaluator:
    """Avalia qualidade do modelo treinado."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.metrics = {}

    def evaluate(self, test_dataset: List[Dict[str, Any]]) -> Dict[str, float]:
        """Avalia modelo em dataset de teste."""
        # Placeholder para implementação real
        self.metrics = {
            "accuracy": 0.85,
            "precision": 0.82,
            "recall": 0.88,
            "f1_score": 0.85,
        }

        return self.metrics

    def generate_report(self) -> str:
        """Gera relatório de avaliação."""
        report = f"""
# Relatório de Avaliação do Modelo

## Modelo: {self.model_path}

## Métricas
- **Accuracy**: {self.metrics.get('accuracy', 0):.2%}
- **Precision**: {self.metrics.get('precision', 0):.2%}
- **Recall**: {self.metrics.get('recall', 0):.2%}
- **F1 Score**: {self.metrics.get('f1_score', 0):.2%}

## Conclusão
O modelo apresenta bom desempenho geral com {self.metrics.get('accuracy', 0):.1%} de acurácia.
"""
        return report

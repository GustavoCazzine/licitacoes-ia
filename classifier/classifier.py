#!/usr/bin/env python3
"""Classificador de editais de licitação via Anthropic API com saída estruturada."""
import json
import os

from anthropic import Anthropic

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic()  # lê ANTHROPIC_API_KEY do ambiente automaticamente
    return _client


_SYSTEM = (
    "Você é especialista em licitações públicas brasileiras para uma empresa de "
    "maquinário pesado e agrícola (Caterpillar, Komatsu, John Deere, Case e similares).\n\n"
    "INCLUIR como relevante=true:\n"
    "- Tratores, retroescavadeiras, motoniveladoras, compactadoras\n"
    "- Motores diesel industriais\n"
    "- Peças e manutenção de frota pesada\n"
    "- Locação de maquinário agrícola ou de construção\n\n"
    "EXCLUIR (relevante=false):\n"
    "- Brinquedos ou miniaturas de maquinário\n"
    "- Maquinário escolar/pedagógico\n"
    "- TI, alimentação, serviços não-mecânicos\n\n"
    "Responda APENAS com o JSON solicitado."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "relevante": {"type": "boolean"},
        "categoria": {
            "type": "string",
            "description": "Ex: trator, retroescavadeira, pecas, manutencao, locacao, irrelevante",
        },
        "confianca": {"type": "number"},
        "motivo": {"type": "string"},
    },
    "required": ["relevante", "categoria", "confianca", "motivo"],
    "additionalProperties": False,
}

# Padrão: claude-opus-4-8 para alta precisão.
# Para reduzir custo em produção, defina CLASSIFIER_MODEL=claude-haiku-4-5 no .env
MODEL = os.getenv("CLASSIFIER_MODEL", "claude-opus-4-8")


def classificar(objeto_raw: str) -> dict:
    """
    Classifica um edital pelo texto do objeto.

    Retorna: {relevante: bool, categoria: str, confianca: float, motivo: str}
    """
    if not objeto_raw or not objeto_raw.strip():
        return {
            "relevante": False,
            "categoria": "indefinido",
            "confianca": 0.0,
            "motivo": "Objeto do edital vazio ou ausente.",
        }

    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=512,
        system=_SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": f"Classifique este objeto de licitação:\n\n{objeto_raw}",
            }
        ],
    )

    text = next(b.text for b in response.content if b.type == "text")
    result = json.loads(text)
    result["confianca"] = round(
        max(0.0, min(1.0, float(result.get("confianca", 0.0)))), 3
    )
    return result

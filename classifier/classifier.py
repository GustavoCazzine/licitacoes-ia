#!/usr/bin/env python3
"""Classificador de editais — suporta Anthropic (pago) e Google Gemini (gratuito)."""
import json
import os

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
    "Responda APENAS com JSON no formato exato:\n"
    '{"relevante": bool, "categoria": string, "confianca": float 0-1, "motivo": string}'
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

# gemini (gratuito, 1500 req/dia) ou anthropic (pago, alta precisão)
PROVIDER = os.getenv("CLASSIFIER_PROVIDER", "anthropic").lower()


def _normalizar(result: dict) -> dict:
    result["confianca"] = round(max(0.0, min(1.0, float(result.get("confianca", 0.0)))), 3)
    result.setdefault("relevante", False)
    result.setdefault("categoria", "indefinido")
    result.setdefault("motivo", "")
    return result


# ── Anthropic ──────────────────────────────────────────────────────────────────

_anthropic_client = None


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic
        _anthropic_client = Anthropic()  # lê ANTHROPIC_API_KEY do ambiente
    return _anthropic_client


def _classificar_anthropic(objeto_raw: str) -> dict:
    model = os.getenv("CLASSIFIER_MODEL", "claude-opus-4-8")
    response = _get_anthropic().messages.create(
        model=model,
        max_tokens=512,
        system=_SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
        messages=[{"role": "user", "content": f"Classifique este objeto de licitação:\n\n{objeto_raw}"}],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return _normalizar(json.loads(text))


# ── Google Gemini (gratuito) ───────────────────────────────────────────────────

def _classificar_gemini(objeto_raw: str) -> dict:
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY não definida. "
            "Obtenha gratuitamente em: aistudio.google.com → Get API key"
        )

    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=_SYSTEM,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    prompt = f"Classifique este objeto de licitação:\n\n{objeto_raw}"
    response = model.generate_content(prompt)
    return _normalizar(json.loads(response.text))


# ── Ponto de entrada ───────────────────────────────────────────────────────────

def classificar(objeto_raw: str) -> dict:
    """Retorna {relevante: bool, categoria: str, confianca: float, motivo: str}."""
    if not objeto_raw or not objeto_raw.strip():
        return {
            "relevante": False,
            "categoria": "indefinido",
            "confianca": 0.0,
            "motivo": "Objeto do edital vazio ou ausente.",
        }

    if PROVIDER == "gemini":
        return _classificar_gemini(objeto_raw)
    return _classificar_anthropic(objeto_raw)

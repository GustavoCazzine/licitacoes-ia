"""Contrato base para scrapers de Diário Oficial municipal."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass
class DiarioOficial:
    municipio: str
    uf: str
    data_publicacao: date
    url_pdf: str
    texto: str
    pdf_hash: str
    usou_ocr: bool = False
    num_paginas: int = 0
    fonte: str = "diario_oficial"
    # Trechos relevantes extraídos do texto (licitação/pregão/dispensa/credenciamento)
    trechos: list[str] = field(default_factory=list)


class BaseScraper(ABC):
    municipio: str
    uf: str
    portal_url: str

    TIMEOUT = 30

    @abstractmethod
    def buscar_edicoes(self, data: date) -> list[DiarioOficial]:
        """
        Busca edições do Diário Oficial publicadas na data informada.
        Retorna lista (pode ser vazia se não houver publicação nesse dia).
        """

    def _extrair_trechos_licitacao(self, texto: str) -> list[str]:
        """
        Extrai parágrafos do texto que contêm termos de licitação.
        Heurística simples para reduzir o volume enviado ao LLM.
        """
        TERMOS = {
            "licitação", "licitacao", "pregão", "pregao",
            "edital", "dispensa", "inexigibilidade", "credenciamento",
            "contratação", "contratacao", "concorrência", "concorrencia",
            "chamamento", "objeto:", "valor estimado",
        }
        paragrafos = [p.strip() for p in texto.split("\n\n") if p.strip()]
        trechos: list[str] = []
        for p in paragrafos:
            lower = p.lower()
            if any(t in lower for t in TERMOS):
                trechos.append(p)
        return trechos

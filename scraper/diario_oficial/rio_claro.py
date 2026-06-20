"""
Scraper do Diário Oficial de Rio Claro, SP.

Portal: https://www.rioclaro.sp.gov.br/diario-oficial/
Rio Claro publica seu DO em PDF no portal oficial com links diretos.
"""
import re
import sys
from datetime import date

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper, DiarioOficial
from .ocr import pdf_hash, pdf_para_texto

_PORTAL_URL = "https://www.rioclaro.sp.gov.br/diario-oficial/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; licitacoes-ia/1.0)"}


class RioClaro(BaseScraper):
    municipio = "Rio Claro"
    uf = "SP"
    portal_url = _PORTAL_URL

    def buscar_edicoes(self, data: date) -> list[DiarioOficial]:
        try:
            resp = requests.get(
                self.portal_url, headers=_HEADERS, timeout=self.TIMEOUT
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[{self.municipio}] Falha ao acessar portal: {exc}", file=sys.stderr)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        links_pdf = _filtrar_links_pdf(soup, data, base_url="https://www.rioclaro.sp.gov.br")

        if not links_pdf:
            print(
                f"[{self.municipio}] Nenhum PDF encontrado para {data}.", file=sys.stderr
            )
            return []

        resultados = []
        for url_pdf in links_pdf:
            do = _baixar_e_processar(url_pdf, self.municipio, self.uf, data, self)
            if do:
                resultados.append(do)
        return resultados


def _filtrar_links_pdf(soup: BeautifulSoup, data: date, base_url: str) -> list[str]:
    padrao_data = re.compile(
        rf"{data.day:02d}[.\-_/]{data.month:02d}[.\-_/]{data.year}"
        rf"|{data.day:02d}{data.month:02d}{data.year}"
        rf"|{data.year}{data.month:02d}{data.day:02d}",
        re.IGNORECASE,
    )

    candidatos: list[str] = []
    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        if not href.lower().endswith(".pdf"):
            continue
        texto_link = a.get_text(strip=True)
        if padrao_data.search(href) or padrao_data.search(texto_link):
            url = href if href.startswith("http") else f"{base_url}{href}"
            candidatos.append(url)

    if not candidatos:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                url = href if href.startswith("http") else f"{base_url}{href}"
                candidatos.append(url)

    return candidatos


def _baixar_e_processar(
    url: str, municipio: str, uf: str, data: date, scraper: BaseScraper
) -> DiarioOficial | None:
    print(f"[{municipio}] Baixando {url}", file=sys.stderr)
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[{municipio}] Erro ao baixar PDF: {exc}", file=sys.stderr)
        return None

    pdf_bytes = resp.content
    hash_ = pdf_hash(pdf_bytes)
    texto, usou_ocr = pdf_para_texto(pdf_bytes)

    do = DiarioOficial(
        municipio=municipio,
        uf=uf,
        data_publicacao=data,
        url_pdf=url,
        texto=texto,
        pdf_hash=hash_,
        usou_ocr=usou_ocr,
    )
    do.trechos = scraper._extrair_trechos_licitacao(texto)
    print(
        f"[{municipio}] OK — {len(texto)} chars, {len(do.trechos)} trechos, OCR={usou_ocr}",
        file=sys.stderr,
    )
    return do

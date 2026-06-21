#!/usr/bin/env python3
"""
Scraper do PNCP (Portal Nacional de Contratações Públicas).
Busca contrações abertas filtradas por UF e imprime JSON estruturado no stdout.

Uso:
    python scraper.py --uf SP --paginas 2
"""

import argparse
import io
import json
import sys
import time
from datetime import date, timedelta

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Garante UTF-8 no stdout mesmo em Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_URL = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"

TIMEOUT = 60

# Modalidades incluídas: Pregão Eletrônico (6), Dispensa (8), Inexigibilidade (9)
MODALIDADES = [6, 8, 9]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; LicitacoesIA/1.0; "
        "+https://github.com/GustavoCazzine/licitacoes-ia)"
    ),
    "Accept": "application/json",
}


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update(_HEADERS)
    return s


def buscar_contratacoes(
    uf: str, data_inicial: str, data_final: str,
    pagina: int = 1, modalidade: int = 6,
) -> dict:
    params = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "uf": uf,
        "pagina": pagina,
        "tamanhoPagina": 50,
        "codigoModalidadeContratacao": modalidade,
    }
    resp = _session().get(BASE_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def normalizar(item: dict) -> dict:
    orgao = item.get("orgaoEntidade", {})
    unidade = item.get("unidadeOrgao", {})
    return {
        "fonte": "pncp",
        "numero_processo": item.get("numeroControlePNCP"),
        "objeto_raw": item.get("objetoCompra"),
        "valor_estimado": item.get("valorTotalEstimado"),
        "data_abertura": item.get("dataAberturaProposta"),
        "link_original": f"https://pncp.gov.br/app/editais/{item.get('numeroControlePNCP', '').replace('/', '-')}",
        "municipio": unidade.get("municipioNome"),
        "uf": unidade.get("ufSigla"),
        "orgao": orgao.get("razaoSocial"),
        "modalidade": item.get("modalidadeNome"),
        "situacao": item.get("situacaoCompraNome"),
    }


def main():
    parser = argparse.ArgumentParser(description="Scraper PNCP/ComprasNet")
    parser.add_argument("--uf", default="SP", help="UF para filtrar (padrão: SP)")
    parser.add_argument("--paginas", type=int, default=1, help="Nº de páginas a buscar (padrão: 1)")
    parser.add_argument("--dias", type=int, default=7, help="Janela de dias retroativos (padrão: 7)")
    args = parser.parse_args()

    hoje = date.today()
    data_final = hoje.strftime("%Y%m%d")
    data_inicial = (hoje - timedelta(days=args.dias)).strftime("%Y%m%d")

    resultados = []
    for modalidade in MODALIDADES:
        for pagina in range(1, args.paginas + 1):
            try:
                dados = buscar_contratacoes(
                    args.uf, data_inicial, data_final, pagina, modalidade
                )
            except requests.HTTPError as exc:
                print(
                    f"[ERRO] Scraper modalidade={modalidade} p.{pagina}: "
                    f"HTTP {exc.response.status_code}",
                    file=sys.stderr,
                )
                break
            except requests.RequestException as exc:
                print(f"[ERRO] Scraper modalidade={modalidade} p.{pagina}: {exc}", file=sys.stderr)
                break

            itens = dados.get("data", [])
            if not itens:
                break

            for item in itens:
                resultados.append(normalizar(item))

            total_paginas = dados.get("totalPaginas", 1)
            if pagina >= total_paginas:
                break

            time.sleep(0.3)  # respeita rate limit do PNCP

    print(json.dumps(resultados, ensure_ascii=False, indent=2))
    print(f"\n# Total: {len(resultados)} contratações", file=sys.stderr)


if __name__ == "__main__":
    main()

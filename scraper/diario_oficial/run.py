#!/usr/bin/env python3
"""
Runner de scrapers de Diário Oficial.

Busca edições de hoje (ou data passada via --data) para os 3 municípios
configurados, extrai trechos de licitação e, opcionalmente, salva no Postgres.

Uso:
    python -m scraper.diario_oficial.run
    python -m scraper.diario_oficial.run --data 2026-06-19 --salvar
"""
import argparse
import io
import json
import os
import sys
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from dotenv import load_dotenv

from .americana import AmericanaScraper
from .piracicaba import PiracicabaScraper
from .rio_claro import RioClaro

load_dotenv()

SCRAPERS = [PiracicabaScraper(), AmericanaScraper(), RioClaro()]


def _pdf_ja_processado(cur, hash_: str) -> bool:
    cur.execute("SELECT 1 FROM editais WHERE pdf_hash = %s LIMIT 1", (hash_,))
    return cur.fetchone() is not None


def _salvar_no_banco(resultados: list[dict]) -> None:
    """
    Persiste trechos de licitação do DO no banco como editais pendentes.

    Deduplicação: o pdf_hash real é gravado apenas no primeiro trecho de cada PDF.
    Na próxima execução, a presença do hash na tabela indica que o PDF já foi
    processado e os demais trechos são ignorados.
    """
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    inseridos = ignorados = 0

    with conn:
        with conn.cursor() as cur:
            for item in resultados:
                hash_ = item["pdf_hash"]

                if _pdf_ja_processado(cur, hash_):
                    print(
                        f"[SKIP] PDF já processado ({hash_[:16]}…): {item['url_pdf']}",
                        file=sys.stderr,
                    )
                    ignorados += 1
                    continue

                for i, trecho in enumerate(item["trechos"]):
                    # pdf_hash apenas no primeiro trecho — marca o PDF como visto
                    cur.execute(
                        """
                        INSERT INTO editais
                          (fonte, objeto_raw, link_original, pdf_hash, status, uf)
                        VALUES (%s, %s, %s, %s, 'pendente', %s)
                        """,
                        (
                            "diario_oficial",
                            trecho,
                            item["url_pdf"],
                            hash_ if i == 0 else None,
                            item.get("uf"),
                        ),
                    )
                    inseridos += 1

    conn.close()
    print(
        f"[DB] {inseridos} trechos inseridos, {ignorados} PDFs já conhecidos.",
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper Diário Oficial Municipal")
    parser.add_argument(
        "--data",
        default=date.today().isoformat(),
        help="Data de publicação (YYYY-MM-DD, padrão: hoje)",
    )
    parser.add_argument(
        "--salvar",
        action="store_true",
        help="Salva trechos no Postgres como editais pendentes",
    )
    args = parser.parse_args()

    data = date.fromisoformat(args.data)
    todos_resultados: list[dict] = []

    for scraper in SCRAPERS:
        print(f"\n=== {scraper.municipio} ({scraper.uf}) ===", file=sys.stderr)
        try:
            edicoes = scraper.buscar_edicoes(data)
        except Exception as exc:
            print(f"[ERRO] {scraper.municipio}: {exc}", file=sys.stderr)
            continue

        for edicao in edicoes:
            resultado = {
                "municipio": edicao.municipio,
                "uf": edicao.uf,
                "data_publicacao": edicao.data_publicacao.isoformat(),
                "url_pdf": edicao.url_pdf,
                "pdf_hash": edicao.pdf_hash,
                "usou_ocr": edicao.usou_ocr,
                "total_chars": len(edicao.texto),
                "num_trechos": len(edicao.trechos),
                "trechos": edicao.trechos,
            }
            todos_resultados.append(resultado)

    # Resumo em stdout (JSON para integração com pipeline)
    saida = [
        {k: v for k, v in r.items() if k != "trechos"}
        for r in todos_resultados
    ]
    print(json.dumps(saida, ensure_ascii=False, indent=2))

    if args.salvar and todos_resultados:
        _salvar_no_banco(todos_resultados)
    elif todos_resultados:
        total_trechos = sum(r["num_trechos"] for r in todos_resultados)
        print(
            f"\n[RESUMO] {len(todos_resultados)} edição(ões), "
            f"{total_trechos} trechos de licitação. "
            f"Use --salvar para persistir no banco.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()

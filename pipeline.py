#!/usr/bin/env python3
"""
Pipeline de ingestão e classificação de editais.
Busca no PNCP → classifica via LLM → persiste no Postgres.

Pré-requisitos:
    pip install -r requirements.txt
    cp .env.example .env  # preencher ANTHROPIC_API_KEY e DATABASE_URL
    docker compose up -d  # Postgres

Uso:
    python pipeline.py [--uf SP] [--paginas 2] [--dias 7]
"""
import argparse
import os
import sys
from datetime import date, datetime, timedelta

import psycopg2
from dotenv import load_dotenv

from scraper.comprasnet.scraper import buscar_contratacoes, normalizar, MODALIDADES
from classifier.classifier import classificar

load_dotenv()

CONFIANCA_MINIMA = float(os.getenv("CONFIANCA_MINIMA", "0.6"))


def _conectar():
    url = os.environ["DATABASE_URL"]
    # Supabase Transaction Pooler requer SSL; adiciona se ausente
    if "sslmode" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return psycopg2.connect(url)


def _edital_existe(cur, fonte: str, numero: str) -> bool:
    cur.execute(
        "SELECT 1 FROM editais WHERE fonte=%s AND numero_processo=%s LIMIT 1",
        (fonte, numero),
    )
    return cur.fetchone() is not None


def _salvar_edital(cur, item: dict, cl: dict) -> int:
    confianca = cl["confianca"]
    relevante = cl["relevante"]
    status = (
        "revisao_manual"
        if relevante and confianca < CONFIANCA_MINIMA
        else "classificado"
    )

    data_abertura = None
    if raw := item.get("data_abertura"):
        try:
            data_abertura = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    cur.execute(
        """
        INSERT INTO editais
          (fonte, numero_processo, objeto_raw, objeto_resumo,
           valor_estimado, data_abertura, link_original,
           classificacao, confianca, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (
            item.get("fonte"),
            item.get("numero_processo"),
            item.get("objeto_raw"),
            cl.get("motivo"),          # motivo como resumo no MVP
            item.get("valor_estimado"),
            data_abertura,
            item.get("link_original"),
            cl.get("categoria"),
            confianca,
            status,
        ),
    )
    return cur.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Pipeline PNCP → LLM → Postgres")
    parser.add_argument("--uf", default="SP", help="UF para filtrar (padrão: SP)")
    parser.add_argument("--paginas", type=int, default=1, help="Páginas do PNCP a buscar")
    parser.add_argument("--dias", type=int, default=7, help="Janela retroativa em dias")
    args = parser.parse_args()

    conn = _conectar()
    print("[DB] Conectado.", file=sys.stderr)

    hoje = date.today()
    data_final = hoje.strftime("%Y%m%d")
    data_inicial = (hoje - timedelta(days=args.dias)).strftime("%Y%m%d")

    novos = relevantes = revisao = erros = 0

    for modalidade in MODALIDADES:
        for pagina in range(1, args.paginas + 1):
            try:
                dados = buscar_contratacoes(
                    args.uf, data_inicial, data_final, pagina, modalidade
                )
            except Exception as exc:
                print(f"[ERRO] Scraper modalidade={modalidade} p.{pagina}: {exc}", file=sys.stderr)
                break

            itens = dados.get("data", [])
            if not itens:
                break

            for raw in itens:
                item = normalizar(raw)
                fonte = item.get("fonte") or "pncp"
                numero = item.get("numero_processo") or ""
                objeto = item.get("objeto_raw") or ""

                if not numero or not objeto:
                    continue

                with conn.cursor() as cur:
                    if _edital_existe(cur, fonte, numero):
                        continue

                try:
                    cl = classificar(objeto)
                except Exception as exc:
                    print(f"[ERRO] LLM '{numero[:40]}': {exc}", file=sys.stderr)
                    erros += 1
                    continue

                try:
                    with conn.cursor() as cur:
                        edital_id = _salvar_edital(cur, item, cl)
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    print(f"[ERRO] DB '{numero[:40]}': {exc}", file=sys.stderr)
                    erros += 1
                    continue

                novos += 1
                if cl["relevante"] and cl["confianca"] >= CONFIANCA_MINIMA:
                    relevantes += 1
                    tag = "RELEVANTE"
                elif cl["relevante"]:
                    revisao += 1
                    tag = "REVISAO"
                else:
                    tag = "irrelevante"

                print(
                    f"  [{edital_id}] {tag} conf={cl['confianca']:.2f}"
                    f" [{cl['categoria']}] {objeto[:55]}",
                    file=sys.stderr,
                )

            if pagina >= dados.get("totalPaginas", 1):
                break

    conn.close()
    print(
        f"\n[RESUMO] novos={novos} relevantes={relevantes}"
        f" revisao_manual={revisao} erros={erros}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()

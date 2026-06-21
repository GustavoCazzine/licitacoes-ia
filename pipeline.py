#!/usr/bin/env python3
"""
Pipeline de ingestão e classificação de editais.
Busca no PNCP → classifica via LLM → persiste no Postgres.

Pré-requisitos:
    pip install -r requirements.txt
    cp .env.example .env  # preencher API keys e DATABASE_URL
    docker compose up -d  # Postgres local

Uso:
    python pipeline.py --uf SP --paginas 2 --dias 7
    python pipeline.py --auto-ufs --paginas 5 --dias 1   # busca UFs dos clientes ativos
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
UF_FALLBACK = os.getenv("CRON_UF", "SP")


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------

def _conectar():
    url = os.environ["DATABASE_URL"]
    if "sslmode" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return psycopg2.connect(url)


def _buscar_ufs_ativas(conn) -> list[str]:
    """
    Retorna a lista de UFs distintas configuradas por clientes ativos com Telegram vinculado.
    Clientes com ufs=[] significam 'todo o Brasil' e não são contabilizados aqui.
    Se nenhum cliente tiver UF configurada, retorna [UF_FALLBACK].
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT jsonb_array_elements_text(filtros->'ufs') AS uf
            FROM clientes
            WHERE filtros ? 'telegram_chat_id'
              AND ativo = true
              AND jsonb_array_length(filtros->'ufs') > 0
            ORDER BY 1
            """
        )
        ufs = [row[0] for row in cur.fetchall()]
    return ufs or [UF_FALLBACK]


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
           classificacao, confianca, status, uf)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (
            item.get("fonte"),
            item.get("numero_processo"),
            item.get("objeto_raw"),
            cl.get("motivo"),
            item.get("valor_estimado"),
            data_abertura,
            item.get("link_original"),
            cl.get("categoria"),
            confianca,
            status,
            item.get("uf"),
        ),
    )
    return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# Ingestão por UF
# ---------------------------------------------------------------------------

def _processar_uf(conn, uf: str, paginas: int, data_inicial: str, data_final: str) -> dict:
    """Busca, classifica e persiste todos os editais do PNCP para uma UF. Retorna contadores."""
    novos = relevantes = revisao = erros = 0

    for modalidade in MODALIDADES:
        for pagina in range(1, paginas + 1):
            try:
                dados = buscar_contratacoes(uf, data_inicial, data_final, pagina, modalidade)
            except Exception as exc:
                print(f"[ERRO] {uf} modalidade={modalidade} p.{pagina}: {exc}", file=sys.stderr)
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
                    f"  [{edital_id}] {uf} {tag} conf={cl['confianca']:.2f}"
                    f" [{cl['categoria']}] {objeto[:50]}",
                    file=sys.stderr,
                )

            if pagina >= dados.get("totalPaginas", 1):
                break

    return {"novos": novos, "relevantes": relevantes, "revisao": revisao, "erros": erros}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Pipeline PNCP → LLM → Postgres")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--uf", default=None, help="UF específica (ex: SP)")
    group.add_argument(
        "--auto-ufs",
        action="store_true",
        help="Busca as UFs configuradas pelos clientes ativos no banco",
    )
    parser.add_argument("--paginas", type=int, default=1, help="Páginas do PNCP por UF (padrão: 1)")
    parser.add_argument("--dias", type=int, default=7, help="Janela retroativa em dias (padrão: 7)")
    args = parser.parse_args()

    conn = _conectar()
    print("[DB] Conectado.", file=sys.stderr)

    if args.auto_ufs:
        ufs = _buscar_ufs_ativas(conn)
        print(f"[AUTO-UFS] Monitorando {len(ufs)} UF(s): {', '.join(ufs)}", file=sys.stderr)
    else:
        ufs = [args.uf or UF_FALLBACK]

    hoje = date.today()
    data_final = hoje.strftime("%Y%m%d")
    data_inicial = (hoje - timedelta(days=args.dias)).strftime("%Y%m%d")

    total = {"novos": 0, "relevantes": 0, "revisao": 0, "erros": 0}

    for uf in ufs:
        print(f"\n[UF] Processando {uf}...", file=sys.stderr)
        resultado = _processar_uf(conn, uf, args.paginas, data_inicial, data_final)
        for k in total:
            total[k] += resultado[k]

    conn.close()
    print(
        f"\n[RESUMO] UFs={len(ufs)} novos={total['novos']} "
        f"relevantes={total['relevantes']} revisao_manual={total['revisao']} "
        f"erros={total['erros']}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Notificador Telegram multi-usuário para editais relevantes.

Para cada cliente com Telegram vinculado, busca editais que:
  1. São relevantes (confiança >= limiar)
  2. Correspondem aos filtros do cliente (categorias e UFs)
  3. Ainda não foram enviados a esse cliente

Uso:
  python -m notifier.telegram
"""
import os
import sys
import time
from datetime import datetime

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CONFIANCA_MINIMA = float(os.getenv("CONFIANCA_MINIMA", "0.6"))

_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ---------------------------------------------------------------------------
# Formatação
# ---------------------------------------------------------------------------

def _formatar_valor(valor) -> str:
    if valor is None:
        return "Não informado"
    try:
        return f"R$ {float(valor):_.2f}".replace("_", ".")
    except (TypeError, ValueError):
        return str(valor)


def _formatar_data(data_abertura) -> str:
    if data_abertura is None:
        return "Não informada"
    if isinstance(data_abertura, datetime):
        return data_abertura.strftime("%d/%m/%Y às %H:%M")
    return str(data_abertura)


def _formatar_mensagem(edital: dict) -> str:
    confianca_pct = int(edital["confianca"] * 100)
    objeto = (edital.get("objeto_resumo") or edital.get("objeto_raw") or "")[:400]
    categoria = edital.get("classificacao") or "—"
    link = edital.get("link_original") or ""
    uf = edital.get("uf") or ""

    linhas = [
        "🔍 <b>Nova Licitação Relevante</b>",
        "",
        f"📋 <b>Objeto:</b> {objeto}",
        f"🏷️ <b>Categoria:</b> {categoria}",
        f"💰 <b>Valor estimado:</b> {_formatar_valor(edital.get('valor_estimado'))}",
        f"📅 <b>Abertura:</b> {_formatar_data(edital.get('data_abertura'))}",
        f"📊 <b>Confiança:</b> {confianca_pct}%",
    ]
    if uf:
        linhas.append(f"📍 <b>UF:</b> {uf}")
    if link:
        linhas.append(f'\n🔗 <a href="{link}">Ver edital</a>')

    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Telegram API
# ---------------------------------------------------------------------------

def _enviar_mensagem(chat_id: str, texto: str) -> bool:
    try:
        resp = requests.post(
            f"{_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": texto, "parse_mode": "HTML"},
            timeout=15,
        )
    except requests.RequestException as exc:
        print(f"[TG] Falha de rede: {exc}", file=sys.stderr)
        return False

    if not resp.ok:
        print(f"[TG] Erro {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
        return False

    return True


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------

def _buscar_clientes(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, filtros
            FROM clientes
            WHERE filtros ? 'telegram_chat_id'
              AND ativo = true
            """
        )
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def _buscar_editais_pendentes(cur, cliente_id: int, confianca_minima: float) -> list[dict]:
    cur.execute(
        """
        SELECT
            e.id,
            e.objeto_raw,
            e.objeto_resumo,
            e.classificacao,
            e.confianca,
            e.valor_estimado,
            e.data_abertura,
            e.link_original,
            e.uf
        FROM editais e
        WHERE e.classificacao IS NOT NULL
          AND e.classificacao NOT IN ('irrelevante', 'indefinido')
          AND e.confianca >= %s
          AND e.status = 'classificado'
          AND NOT EXISTS (
              SELECT 1 FROM alertas_enviados a
              WHERE a.edital_id = e.id AND a.cliente_id = %s
          )
        ORDER BY e.created_at DESC
        LIMIT 100
        """,
        (confianca_minima, cliente_id),
    )
    cols = [desc[0] for desc in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _corresponde_filtros(edital: dict, filtros: dict) -> bool:
    """Retorna True se o edital atende aos filtros de categoria e UF do cliente."""
    categorias = filtros.get("categorias") or []
    ufs = filtros.get("ufs") or []

    if categorias and edital.get("classificacao") not in categorias:
        return False

    if ufs and edital.get("uf") not in ufs:
        return False

    return True


def _registrar_alerta(conn, edital_id: int, cliente_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO alertas_enviados (edital_id, cliente_id, canal) VALUES (%s, %s, 'telegram')",
            (edital_id, cliente_id),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def notificar() -> int:
    """
    Envia alertas Telegram personalizados para cada cliente ativo.
    Retorna o total de alertas enviados com sucesso.
    """
    url = os.environ["DATABASE_URL"]
    if "sslmode" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    conn = psycopg2.connect(url)

    clientes = _buscar_clientes(conn)
    print(f"[TG] {len(clientes)} cliente(s) com Telegram vinculado.", file=sys.stderr)

    total_enviados = 0

    for cliente in clientes:
        cliente_id = cliente["id"]
        filtros = cliente["filtros"]
        chat_id = filtros.get("telegram_chat_id")

        with conn.cursor() as cur:
            pendentes = _buscar_editais_pendentes(cur, cliente_id, CONFIANCA_MINIMA)

        correspondentes = [e for e in pendentes if _corresponde_filtros(e, filtros)]
        print(
            f"[TG] Cliente {cliente_id}: {len(pendentes)} pendentes, "
            f"{len(correspondentes)} correspondem aos filtros.",
            file=sys.stderr,
        )

        for edital in correspondentes:
            texto = _formatar_mensagem(edital)
            ok = _enviar_mensagem(chat_id, texto)

            if ok:
                _registrar_alerta(conn, edital["id"], cliente_id)
                total_enviados += 1
                print(f"[TG] Enviado — edital #{edital['id']} → cliente {cliente_id}", file=sys.stderr)
            else:
                print(f"[TG] Falha — edital #{edital['id']} → cliente {cliente_id}", file=sys.stderr)

            time.sleep(0.5)

    conn.close()
    print(f"[TG] Concluído: {total_enviados} alerta(s) enviado(s).", file=sys.stderr)
    return total_enviados


if __name__ == "__main__":
    notificar()

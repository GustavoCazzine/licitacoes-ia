#!/usr/bin/env python3
"""
Notificador Telegram para editais relevantes.

Lê da tabela editais os registros classificados como relevantes
(classificacao != 'irrelevante', confianca >= limiar) sem alerta enviado ainda,
envia mensagem via Telegram Bot API e registra em alertas_enviados.

Setup (uma única vez):
  1. Abra @BotFather no Telegram → /newbot → copie o token
  2. Adicione o bot ao grupo/canal desejado ou inicie conversa direta
  3. Para obter o TELEGRAM_CHAT_ID:
       https://api.telegram.org/bot<TOKEN>/getUpdates
     O campo "chat.id" aparece após enviar qualquer mensagem ao bot.
  4. Preencha TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env

Uso:
  python -m notifier.telegram
"""
import json
import os
import sys
import time
from datetime import datetime

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DEFAULT_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
CONFIANCA_MINIMA = float(os.getenv("CONFIANCA_MINIMA", "0.6"))

_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ---------------------------------------------------------------------------
# Formatação de mensagem
# ---------------------------------------------------------------------------

def _formatar_valor(valor) -> str:
    if valor is None:
        return "Não informado"
    try:
        return f"R$ {float(valor):_.2f}".replace("_", ".").replace(",", ",")
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

    linhas = [
        "🔍 <b>Nova Licitação Relevante</b>",
        "",
        f"📋 <b>Objeto:</b> {objeto}",
        f"🏷️ <b>Categoria:</b> {categoria}",
        f"💰 <b>Valor estimado:</b> {_formatar_valor(edital.get('valor_estimado'))}",
        f"📅 <b>Abertura:</b> {_formatar_data(edital.get('data_abertura'))}",
        f"📊 <b>Confiança:</b> {confianca_pct}%",
    ]
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

def _get_or_create_cliente(conn, chat_id: str) -> int:
    """Garante que exista um registro em clientes para este chat_id."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM clientes WHERE filtros->>'telegram_chat_id' = %s LIMIT 1",
            (chat_id,),
        )
        row = cur.fetchone()
        if row:
            return row[0]

        cur.execute(
            "INSERT INTO clientes (nome, filtros) VALUES (%s, %s::jsonb) RETURNING id",
            ("Telegram Default", json.dumps({"telegram_chat_id": chat_id})),
        )
        cliente_id = cur.fetchone()[0]
    conn.commit()
    return cliente_id


def _buscar_pendentes(cur, confianca_minima: float) -> list[dict]:
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
            e.link_original
        FROM editais e
        WHERE e.classificacao IS NOT NULL
          AND e.classificacao NOT IN ('irrelevante', 'indefinido')
          AND e.confianca >= %s
          AND e.status = 'classificado'
          AND NOT EXISTS (
              SELECT 1 FROM alertas_enviados a WHERE a.edital_id = e.id
          )
        ORDER BY e.created_at DESC
        LIMIT 50
        """,
        (confianca_minima,),
    )
    cols = [desc[0] for desc in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _registrar_alerta(conn, edital_id: int, cliente_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO alertas_enviados (edital_id, cliente_id, canal) VALUES (%s, %s, 'telegram')",
            (edital_id, cliente_id),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Entrada principal
# ---------------------------------------------------------------------------

def notificar() -> int:
    """
    Envia alertas Telegram para editais relevantes ainda não notificados.
    Retorna o número de alertas enviados com sucesso.
    """
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cliente_id = _get_or_create_cliente(conn, DEFAULT_CHAT_ID)

    with conn.cursor() as cur:
        pendentes = _buscar_pendentes(cur, CONFIANCA_MINIMA)

    print(f"[TG] {len(pendentes)} edital(is) para notificar.", file=sys.stderr)
    enviados = 0

    for edital in pendentes:
        texto = _formatar_mensagem(edital)
        ok = _enviar_mensagem(DEFAULT_CHAT_ID, texto)

        if ok:
            _registrar_alerta(conn, edital["id"], cliente_id)
            enviados += 1
            print(f"[TG] Alerta enviado — edital #{edital['id']}", file=sys.stderr)
        else:
            print(f"[TG] Falha — edital #{edital['id']}", file=sys.stderr)

        time.sleep(0.5)  # rate limit: Telegram permite ~30 msg/s, mas 0.5s é seguro

    conn.close()
    print(f"[TG] Concluído: {enviados}/{len(pendentes)} enviados.", file=sys.stderr)
    return enviados


if __name__ == "__main__":
    notificar()

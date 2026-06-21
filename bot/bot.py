#!/usr/bin/env python3
"""
Bot Telegram — vinculação de conta e consulta de status.

Comandos:
  /start <TOKEN>  vincula sua conta usando o token do painel web
  /start          exibe instruções
  /status         mostra filtros ativos da conta vinculada
  /parar          desvincula a conta (para de receber alertas)

Uso:
  python -m bot.bot
"""
import json
import logging
import os
import sys

import psycopg2
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    stream=sys.stderr,
)
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

LABEL_CATEGORIA = {
    "trator": "Tratores",
    "retroescavadeira": "Retroescavadeiras",
    "motoniveladora": "Motoniveladoras",
    "motor_diesel": "Motores diesel",
    "pecas": "Peças de frota",
    "manutencao": "Manutenção de frota",
    "locacao": "Locação de maquinário",
}


def _conectar():
    url = os.environ["DATABASE_URL"]
    if "sslmode" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return psycopg2.connect(url)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    args = context.args or []

    if not args:
        await update.message.reply_text(
            "👋 Olá! Para receber alertas de licitações relevantes:\n\n"
            "1. Acesse o painel web → Configurações\n"
            "2. Copie seu token de vinculação\n"
            "3. Envie aqui: /start SEU_TOKEN",
        )
        return

    token = args[0].upper()
    conn = _conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, nome FROM clientes WHERE filtros->>'telegram_token' = %s LIMIT 1",
                (token,),
            )
            row = cur.fetchone()

        if not row:
            await update.message.reply_text(
                "❌ Token inválido. Verifique o código na página Configurações do painel.",
            )
            return

        cliente_id, nome = row
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE clientes SET filtros = filtros || %s::jsonb WHERE id = %s",
                (json.dumps({"telegram_chat_id": chat_id}), cliente_id),
            )
        conn.commit()
        log.info("Vinculado: cliente_id=%s chat_id=%s", cliente_id, chat_id)

        primeiro_nome = nome.split()[0] if nome else "!"
        await update.message.reply_text(
            f"✅ Conta vinculada, {primeiro_nome}!\n\n"
            "Você receberá alertas de licitações relevantes diretamente aqui.\n\n"
            "• /status — ver suas configurações\n"
            "• /parar — cancelar alertas",
        )
    finally:
        conn.close()


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    conn = _conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT nome, filtros FROM clientes WHERE filtros->>'telegram_chat_id' = %s LIMIT 1",
                (chat_id,),
            )
            row = cur.fetchone()

        if not row:
            await update.message.reply_text(
                "Conta não vinculada. Use /start TOKEN para conectar.",
            )
            return

        nome, filtros = row
        categorias = filtros.get("categorias") or []
        ufs = filtros.get("ufs") or []

        cats = ", ".join(LABEL_CATEGORIA.get(c, c) for c in categorias) if categorias else "Todas"
        regioes = ", ".join(ufs) if ufs else "Todo o Brasil"

        await update.message.reply_text(
            f"👤 <b>{nome}</b>\n\n"
            f"📋 <b>Categorias:</b> {cats}\n"
            f"📍 <b>Regiões:</b> {regioes}\n\n"
            "Para alterar, acesse o painel → Configurações.",
            parse_mode="HTML",
        )
    finally:
        conn.close()


async def cmd_parar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    conn = _conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE clientes "
                "SET filtros = filtros - 'telegram_chat_id' "
                "WHERE filtros->>'telegram_chat_id' = %s",
                (chat_id,),
            )
            afetados = cur.rowcount
        conn.commit()

        if afetados:
            await update.message.reply_text(
                "🔕 Conta desvinculada. Você não receberá mais alertas.\n"
                "Use /start TOKEN para reconectar quando quiser.",
            )
        else:
            await update.message.reply_text("Sua conta não estava vinculada.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("parar", cmd_parar))

    log.info("Bot iniciado. Aguardando comandos (Ctrl+C para encerrar)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

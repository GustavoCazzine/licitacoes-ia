#!/usr/bin/env python3
"""
Agendador diário de ingestão de licitações.

Sequência diária:
  CRON_HORA_PNCP    (padrão 07:00) — pipeline PNCP → LLM → DB → Telegram
  CRON_HORA_DIARIOS (padrão 07:30) — scrapers Diário Oficial → DB → Telegram

Variáveis de ambiente (.env):
  CRON_HORA_PNCP=07:00
  CRON_HORA_DIARIOS=07:30
  CRON_UF=SP
  CRON_PAGINAS=5
  CRON_DIAS=1        # janela retroativa para o PNCP

Uso:
  python cron.py            # daemon contínuo
  python cron.py --agora    # executa os dois jobs imediatamente e sai
"""
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime

import schedule
from dotenv import load_dotenv

load_dotenv()

HORA_PNCP = os.getenv("CRON_HORA_PNCP", "07:00")
HORA_DIARIOS = os.getenv("CRON_HORA_DIARIOS", "07:30")
UF = os.getenv("CRON_UF", "SP")
PAGINAS = os.getenv("CRON_PAGINAS", "5")
DIAS = os.getenv("CRON_DIAS", "1")


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)


def _rodar(*cmd: str) -> None:
    _log(f"Iniciando: {' '.join(cmd)}")
    result = subprocess.run(cmd, text=True)
    if result.returncode == 0:
        _log(f"OK: {cmd[1]}")
    else:
        _log(f"ERRO (código {result.returncode}): {cmd[1]}")


def _notificar() -> None:
    _rodar(sys.executable, "-m", "notifier.telegram")


def job_pncp() -> None:
    _rodar(
        sys.executable, "pipeline.py",
        "--uf", UF,
        "--paginas", PAGINAS,
        "--dias", DIAS,
    )
    _notificar()


def job_diarios() -> None:
    _rodar(
        sys.executable, "-m", "scraper.diario_oficial.run",
        "--salvar",
    )
    _notificar()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cron de ingestão de licitações")
    parser.add_argument(
        "--agora",
        action="store_true",
        help="Executa os dois jobs imediatamente e encerra (útil para testes)",
    )
    args = parser.parse_args()

    if args.agora:
        _log("Execução imediata solicitada.")
        job_pncp()
        job_diarios()
        return

    schedule.every().day.at(HORA_PNCP).do(job_pncp)
    schedule.every().day.at(HORA_DIARIOS).do(job_diarios)

    _log(f"Cron iniciado. PNCP às {HORA_PNCP}, Diários às {HORA_DIARIOS}.")
    _log("Pressione Ctrl+C para encerrar.")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()

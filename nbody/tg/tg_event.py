#!/usr/bin/env python3
"""
tg_event.py — скрипт одноразовых Telegram-уведомлений о событиях симуляции.

Использует tg_notify.TgNotify для отправки сообщений.

Вызов:
    python3 tg_event.py --event start   --name myrun --type sidm --sigma 10
    python3 tg_event.py --event finish  --name myrun --status 0
    python3 tg_event.py --event progress --state /nbody/runs/myrun/run.state
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Добавляем родительскую директорию для импорта tg_notify
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tg_notify import TgNotify, ConfigError, TelegramAPIError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("tg_event")


class StateAdapter:
    """
    Адаптер для парсинга run.state.
    Изолирует формат state-файла от остального кода.
    При изменении формата достаточно поправить только этот класс.
    """

    REQUIRED_FIELDS = ["STATUS", "RUN_NAME"]
    OPTIONAL_FIELDS = [
        "SIM_TYPE", "SIGMA", "TIME", "TIME_MAX", "PROGRESS",
        "SYNC_POINT", "SNAPSHOTS", "MEM_MB", "ELAPSED_MIN", "TIMESTAMP"
    ]

    @staticmethod
    def parse(state_path: str) -> Optional[dict]:
        """
        Парсит state-файл в словарь.
        Возвращает None, если файла нет или он пуст.
        """
        if not os.path.isfile(state_path):
            return None

        result = {}
        try:
            with open(state_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    result[key.strip()] = val.strip()
        except (OSError, IOError) as e:
            logger.warning("Ошибка чтения state-файла %s: %s", state_path, e)
            return None

        # Проверяем обязательные поля
        for field in StateAdapter.REQUIRED_FIELDS:
            if field not in result:
                logger.warning("State-файл %s не содержит поле %s", state_path, field)
                return None

        return result

    @staticmethod
    def format_status(state: dict) -> str:
        """Форматирует словарь state в читаемое сообщение."""
        run_name = state.get("RUN_NAME", "?")
        sim_type = state.get("SIM_TYPE", "?")
        status = state.get("STATUS", "?")
        time_val = state.get("TIME", "?")
        time_max = state.get("TIME_MAX", "?")
        progress = state.get("PROGRESS", "?")
        snaps = state.get("SNAPSHOTS", "?")
        mem = state.get("MEM_MB", "?")
        elapsed = state.get("ELAPSED_MIN", "?")
        sigma = state.get("SIGMA", "N/A")
        sync = state.get("SYNC_POINT", "?")

        lines = [
            f"📊 *Статус: {run_name}*",
            f"Тип: {sim_type}  σ: {sigma}",
            f"Статус: {status}",
            f"Время: {time_val} / {time_max}  ({progress})",
            f"Синк-поинт: {sync}",
            f"Снапшотов: {snaps}",
            f"Память: {mem} MB",
            f"Прошло: {elapsed} мин",
        ]
        return "\n".join(lines)


def build_start_message(args) -> str:
    """Формирует сообщение о старте симуляции."""
    msg = [
        "🚀 *Симуляция запущена*",
        f"Имя: `{args.name}`",
        f"Тип: {args.type.upper()}",
    ]
    if args.sigma and args.sigma != "N/A":
        msg.append(f"σ: {args.sigma} см²/г")
    if args.ic:
        msg.append(f"IC: {args.ic}")
    if args.time_max:
        msg.append(f"TimeMax: {args.time_max}")
    return "\n".join(msg)


def build_finish_message(args) -> str:
    """Формирует сообщение о завершении симуляции."""
    status_int = int(args.status) if args.status and args.status.isdigit() else -1

    if status_int == 0:
        header = f"✅ *Симуляция завершена: {args.name}*"
    elif status_int == -1:
        header = f"⚠️ *Симуляция: {args.name} — статус неизвестен*"
    else:
        msg_parts = [f"❌ *Симуляция упала: {args.name}*"]
        msg_parts.append(f"Exit code: `{args.status}`")
        if args.status in ["139", "-11"]:
            msg_parts.append("Возможная причина: SIGSEGV (падение памяти)")
        elif args.status in ["134", "-6"]:
            msg_parts.append("Возможная причина: SIGABRT (assertion failed)")
        msg_parts.append(f"Лог: `/nbody/runs/{args.name}/run.log`")
        return "\n".join(msg_parts)

    # Для успешного завершения — пробуем достать статистику из state-файла
    lines = [header]
    if args.state:
        state = StateAdapter.parse(args.state)
        if state:
            elapsed = state.get("ELAPSED_MIN", "?")
            snaps = state.get("SNAPSHOTS", "?")
            lines.append(f"Время выполнения: {elapsed} мин")
            lines.append(f"Снапшотов: {snaps}")

    lines.append(f"Директория: `/nbody/runs/{args.name}/`")
    return "\n".join(lines)


def build_progress_message(state_path: str) -> Optional[str]:
    """Формирует сообщение о прогрессе из state-файла."""
    state = StateAdapter.parse(state_path)
    if not state:
        return None

    return StateAdapter.format_status(state)


def send_start(tg: TgNotify, args) -> bool:
    """Отправляет уведомление о старте."""
    msg = build_start_message(args)
    try:
        tg.send_message(msg)
        logger.info("Отправлено уведомление START для %s", args.name)
        return True
    except TelegramAPIError as e:
        logger.error("Ошибка отправки START: %s", e)
        return False


def send_finish(tg: TgNotify, args) -> bool:
    """Отправляет уведомление о завершении."""
    msg = build_finish_message(args)
    try:
        tg.send_message(msg)
        logger.info("Отправлено уведомление FINISH для %s (status=%s)", args.name, args.status)
        return True
    except TelegramAPIError as e:
        logger.error("Ошибка отправки FINISH: %s", e)
        return False


def send_progress(tg: TgNotify, args) -> bool:
    """Отправляет уведомление о прогрессе из state-файла."""
    if not args.state or not os.path.isfile(args.state):
        logger.warning("State-файл не указан или не существует: %s", args.state)
        return False

    msg = build_progress_message(args.state)
    if not msg:
        logger.warning("Не удалось сформировать сообщение прогресса (state пуст?)")
        return False

    try:
        tg.send_message(msg)
        name = args.name or os.path.basename(os.path.dirname(args.state))
        logger.info("Отправлено уведомление PROGRESS для %s", name)
        return True
    except TelegramAPIError as e:
        logger.error("Ошибка отправки PROGRESS: %s", e)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Telegram-уведомления о событиях симуляции",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python3 tg_event.py --event start --name myrun --type sidm --sigma 10
  python3 tg_event.py --event finish --name myrun --status 0
  python3 tg_event.py --event progress --state /nbody/runs/myrun/run.state
        """,
    )
    parser.add_argument(
        "--event", required=True,
        choices=["start", "finish", "progress"],
        help="Тип события"
    )
    parser.add_argument("--name", help="Имя прогона")
    parser.add_argument("--type", choices=["cdm", "sidm"], help="Тип симуляции")
    parser.add_argument("--sigma", default="N/A", help="Сечение SIDM")
    parser.add_argument("--ic", default="", help="Имя IC-файла")
    parser.add_argument("--time-max", default="", help="TimeMax")
    parser.add_argument("--status", default="0", help="Exit code симуляции")
    parser.add_argument("--state", help="Путь к run.state")

    args = parser.parse_args()

    # Инициализируем TgNotify
    try:
        tg = TgNotify()
    except ConfigError as e:
        logger.error("Ошибка конфигурации Telegram: %s", e)
        sys.exit(1)

    # Выполняем действие
    success = False
    if args.event == "start":
        if not args.name or not args.type:
            logger.error("Для --event start требуется --name и --type")
            sys.exit(1)
        success = send_start(tg, args)

    elif args.event == "finish":
        if not args.name:
            logger.error("Для --event finish требуется --name")
            sys.exit(1)
        success = send_finish(tg, args)

    elif args.event == "progress":
        if not args.state:
            logger.error("Для --event progress требуется --state <path>")
            sys.exit(1)
        success = send_progress(tg, args)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
tgbot.py — Polling Telegram-бот для мониторинга симуляций.

Возможности:
  - Команды: /start, /help, /status, /runs
  - Фоновый мониторинг run.state-файлов каждые N часов
  - Dedup-кэш (не отправляет одинаковые уведомления дважды)
  - Логирование в /nbody/tg/tgbot.log
  - Авто-реконнект при сетевых ошибках

Запуск:
  python3 /nbody/tg/tgbot.py &
  tail -f /nbody/tg/tgbot.log
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Настраиваем логирование ДО импорта остального
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tgbot.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("tgbot")

# Добавляем директорию для импорта tg_notify
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tg_notify import TgNotify, ConfigError, TelegramAPIError

# =============================================================================
# Конфигурация
# =============================================================================

RUNS_DIR = "/nbody/runs"
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tgbot_state.json")
MONITOR_INTERVAL_HOURS = 2       # проверка состояния симуляций раз в 2 часа
PROGRESS_INTERVAL_HOURS = 4      # прогресс отправляется не чаще чем раз в 4 часа

# =============================================================================
# DedupCache — защита от дублирования уведомлений
# =============================================================================

class DedupCache:
    """
    Persistent JSON-файл, хранящий хеши отправленных событий.
    Ключ: "{run_name}_{event_type}"  (например "myrun_finish")
    Значение: ISO-время отправки.
    """

    def __init__(self, path: str):
        self.path = path
        self._data: dict = {}
        self._load()

    def _load(self):
        if os.path.isfile(self.path):
            try:
                with open(self.path) as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Ошибка чтения кэша %s: %s. Создаём новый.", self.path, e)
                self._data = {}
        else:
            self._data = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def was_sent(self, run_name: str, event_type: str) -> bool:
        """Проверяет, было ли уже отправлено это событие."""
        key = f"{run_name}_{event_type}"
        return key in self._data

    def mark_sent(self, run_name: str, event_type: str):
        """Отмечает событие как отправленное."""
        key = f"{run_name}_{event_type}"
        self._data[key] = datetime.utcnow().isoformat()
        self._save()

    def last_sent(self, run_name: str, event_type: str) -> Optional[datetime]:
        """Возвращает время последней отправки события, или None."""
        key = f"{run_name}_{event_type}"
        val = self._data.get(key)
        if val:
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                return None
        return None

    def clear_run(self, run_name: str):
        """Очищает все события для указанного прогона."""
        prefix = f"{run_name}_"
        to_delete = [k for k in self._data if k.startswith(prefix)]
        for k in to_delete:
            del self._data[k]
        if to_delete:
            self._save()


# =============================================================================
# StateAdapter — изолированный парсер run.state
# =============================================================================

class StateAdapter:
    """Парсит run.state в структурированный словарь."""

    @staticmethod
    def parse(state_path: str) -> Optional[dict]:
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
        if "STATUS" not in result or "RUN_NAME" not in result:
            return None
        return result

    @staticmethod
    def format_short(state: dict) -> str:
        """Краткое форматирование (для списка прогонов)."""
        return (
            f"{state.get('RUN_NAME', '?'):30s} "
            f"{state.get('STATUS', '?'):10s} "
            f"{state.get('TIME', '?'):>8s} / {state.get('TIME_MAX', '?'):>8s}"
        )

    @staticmethod
    def format_detailed(state: dict) -> str:
        """Полное форматирование (для /status)."""
        lines = [
            f"📊 *{state.get('RUN_NAME', '?')}*",
            f"Статус: {state.get('STATUS', '?')}",
            f"Тип: {state.get('SIM_TYPE', '?')} | σ: {state.get('SIGMA', 'N/A')}",
            f"Время: {state.get('TIME', '?')} / {state.get('TIME_MAX', '?')} ({state.get('PROGRESS', '?')})",
            f"Синк-поинт: {state.get('SYNC_POINT', '?')}",
            f"Снапшотов: {state.get('SNAPSHOTS', '?')}",
            f"Память: {state.get('MEM_MB', '?')} MB",
            f"Прошло: {state.get('ELAPSED_MIN', '?')} мин",
        ]
        return "\n".join(lines)


# =============================================================================
# SimulationMonitor — фоновый мониторинг симуляций
# =============================================================================

@dataclass
class SimulationInfo:
    """Модель данных о прогоне."""
    run_name: str
    status: str          # RUNNING | COMPLETED | FAILED | NOT START
    state_path: str
    state: Optional[dict] = None
    has_output: bool = False


class SimulationMonitor:
    """
    Фоновый мониторинг: сканирует nbody/runs/*/run.state,
    отправляет уведомления о новых событиях.
    """

    def __init__(self, bot_notifier: 'BotNotifier', dedup: DedupCache,
                 interval_hours: int = MONITOR_INTERVAL_HOURS):
        self.notifier = bot_notifier
        self.dedup = dedup
        self.interval = interval_hours
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def run(self):
        """Запускает цикл мониторинга."""
        self._running = True
        logger.info("Монитор запущен (интервал: %d ч)", self.interval)

        # Первый проход — через 30 секунд после старта бота
        await asyncio.sleep(30)
        await self._scan()

        while self._running:
            await asyncio.sleep(self.interval * 3600)
            await self._scan()

    def stop(self):
        """Останавливает мониторинг."""
        self._running = False
        logger.info("Монитор остановлен")

    async def _scan(self):
        """Сканирует все прогоны и отправляет уведомления."""
        logger.info("Сканирование симуляций в %s", RUNS_DIR)

        if not os.path.isdir(RUNS_DIR):
            logger.warning("Директория %s не существует", RUNS_DIR)
            return

        runs = []
        for entry in os.scandir(RUNS_DIR):
            if not entry.is_dir():
                continue
            run_name = entry.name
            state_path = os.path.join(entry.path, "run.state")

            if os.path.isfile(state_path):
                state = StateAdapter.parse(state_path)
                if state:
                    status = state.get("STATUS", "UNKNOWN")
                    runs.append(SimulationInfo(
                        run_name=run_name,
                        status=status,
                        state_path=state_path,
                        state=state,
                        has_output=os.path.isdir(os.path.join(entry.path, "output")),
                    ))
            else:
                # Нет state-файла — определяем статус по наличию output
                has_output = os.path.isdir(os.path.join(entry.path, "output"))
                has_snaps = False
                if has_output:
                    snap_dir = os.path.join(entry.path, "output")
                    has_snaps = any(f.startswith("snapshot_") for f in os.listdir(snap_dir)) if os.path.isdir(snap_dir) else False
                status = "COMPLETED" if has_snaps else "NOT START"
                runs.append(SimulationInfo(
                    run_name=run_name,
                    status=status,
                    state_path=state_path,
                    has_output=has_output,
                ))

        # Обрабатываем каждый прогон
        for sim in runs:
            await self._process_run(sim)

    async def _process_run(self, sim: SimulationInfo):
        """Обрабатывает один прогон: решает, нужно ли уведомление."""
        run_name = sim.run_name

        # Игнорируем "NOT START" — это пустые папки
        if sim.status == "NOT START":
            return

        # COMPLETED — отправляем финиш (только один раз)
        if sim.status == "COMPLETED":
            if not self.dedup.was_sent(run_name, "finish"):
                msg = f"✅ *Симуляция завершена: {run_name}*"
                if sim.state:
                    elapsed = sim.state.get("ELAPSED_MIN", "?")
                    snaps = sim.state.get("SNAPSHOTS", "?")
                    msg += f"\nВремя выполнения: {elapsed} мин\nСнапшотов: {snaps}"
                msg += f"\nДиректория: `{RUNS_DIR}/{run_name}/`"
                await self.notifier.send(msg)
                self.dedup.mark_sent(run_name, "finish")
                logger.info("Уведомление о завершении: %s", run_name)
            return

        # FAILED — отправляем ошибку (только один раз)
        if sim.status == "FAILED":
            if not self.dedup.was_sent(run_name, "finish"):
                msg = f"❌ *Симуляция упала: {run_name}*\nЛог: `{RUNS_DIR}/{run_name}/run.log`"
                await self.notifier.send(msg)
                self.dedup.mark_sent(run_name, "finish")
                logger.info("Уведомление об ошибке: %s", run_name)
            return

        # RUNNING — отправляем прогресс, если прошло > N часов с последнего
        if sim.status == "RUNNING" and sim.state:
            last_progress = self.dedup.last_sent(run_name, "progress")
            now = datetime.utcnow()
            if last_progress is None or (now - last_progress).total_seconds() > PROGRESS_INTERVAL_HOURS * 3600:
                msg = StateAdapter.format_detailed(sim.state)
                msg = f"⏳ *Прогресс*\n{msg}"
                await self.notifier.send(msg)
                self.dedup.mark_sent(run_name, "progress")
                logger.info("Уведомление о прогрессе: %s", run_name)

    async def force_status(self) -> str:
        """Формирует полный отчёт по всем симуляциям (для /status)."""
        if not os.path.isdir(RUNS_DIR):
            return "Директория прогонов не найдена."

        lines = ["📋 *Все симуляции:*\n"]
        found = False

        for entry in sorted(os.scandir(RUNS_DIR), key=lambda e: e.name):
            if not entry.is_dir():
                continue
            state_path = os.path.join(entry.path, "run.state")
            found = True

            if os.path.isfile(state_path):
                state = StateAdapter.parse(state_path)
                if state:
                    lines.append(StateAdapter.format_short(state))
                else:
                    lines.append(f"{entry.name:30s} BROKEN-STATE")
            else:
                has_snaps = False
                output_dir = os.path.join(entry.path, "output")
                if os.path.isdir(output_dir):
                    has_snaps = any(f.startswith("snapshot_") for f in os.listdir(output_dir))
                status = "COMPLETED" if has_snaps else "NOT START"
                lines.append(f"{entry.name:30s} {status:10s}")

        if not found:
            return "Нет прогонов в директории."

        return "\n".join(lines)


# =============================================================================
# BotNotifier — обёртка над TgNotify для асинхронной отправки
# =============================================================================

class BotNotifier:
    """Асинхронная обёртка для отправки сообщений через TgNotify."""

    def __init__(self, tg: TgNotify):
        self._tg = tg
        self._last_error_time = 0
        self._error_count = 0
        self._max_errors = 10  # после 10 ошибок подряд прекращаем попытки

    async def send(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Асинхронная отправка сообщения (через loop.run_in_executor)."""
        def _sync_send():
            try:
                self._tg.send_message(text, parse_mode=parse_mode)
                self._error_count = 0
                return True
            except TelegramAPIError as e:
                logger.error("Ошибка отправки: %s", e)
                self._error_count += 1
                self._last_error_time = time.time()
                return False

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_send)

    @property
    def is_blocked(self) -> bool:
        """Проверяет, не превышен ли лимит ошибок."""
        if self._error_count >= self._max_errors:
            # Если прошло больше часа — сбрасываем счётчик
            if time.time() - self._last_error_time > 3600:
                self._error_count = 0
                return False
            return True
        return False


# =============================================================================
# Telegram Bot (python-telegram-bot v20+)
# =============================================================================

async def cmd_start(update, context):
    """Обработчик /start."""
    msg = (
        "👋 *Привет! Я бот для мониторинга N-body симуляций.*\n\n"
        "Команды:\n"
        "/status — текущий статус всех симуляций\n"
        "/runs — список всех прогонов\n"
        "/help — эта справка\n\n"
        "Я также присылаю уведомления о завершении симуляций."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_help(update, context):
    """Обработчик /help."""
    await cmd_start(update, context)


async def cmd_status(update, context):
    """Обработчик /status — показывает статус последнего активного прогона."""
    monitor: SimulationMonitor = context.bot_data.get("monitor")
    if not monitor:
        await update.message.reply_text("Монитор не инициализирован.")
        return

    status_text = await monitor.force_status()
    await update.message.reply_text(status_text, parse_mode="Markdown")


async def cmd_runs(update, context):
    """Обработчик /runs — показывает список всех прогонов."""
    monitor: SimulationMonitor = context.bot_data.get("monitor")
    if not monitor:
        await update.message.reply_text("Монитор не инициализирован.")
        return

    status_text = await monitor.force_status()
    await update.message.reply_text(status_text, parse_mode="Markdown")


# =============================================================================
# Error handling
# =============================================================================

async def error_handler(update, context):
    """Глобальный обработчик ошибок python-telegram-bot."""
    logger.error("Ошибка в боте: %s", context.error, exc_info=True)

    # Пытаемся уведомить пользователя
    try:
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Внутренняя ошибка бота. Подробности в логе.",
            )
    except Exception:
        pass


# =============================================================================
# Main
# =============================================================================

def main():
    # Читаем конфиг Telegram
    try:
        tg = TgNotify()
    except ConfigError as e:
        logger.error("Ошибка конфигурации Telegram: %s", e)
        sys.exit(1)

    notifier = BotNotifier(tg)
    dedup = DedupCache(CACHE_FILE)

    # Проверяем установлен ли python-telegram-bot
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes
    except ImportError:
        logger.error(
            "python-telegram-bot не установлен. Выполните: docker exec gadget-gizmo pip install python-telegram-bot"
        )
        sys.exit(1)

    # Стартовое сообщение через 5 секунд после старта бота
    async def _delayed_startup():
        await asyncio.sleep(5)
        await notifier.send("✅ *tgbot запущен*\nМониторинг активен (интервал: {} ч)".format(MONITOR_INTERVAL_HOURS))

    # Создаём монитор
    monitor = SimulationMonitor(notifier, dedup)

    # post_init — вызывается внутри run_polling, когда event loop уже работает
    async def _post_init(app):
        app.bot_data["monitor"] = monitor
        # Запускаем мониторинг в фоне
        asyncio.create_task(monitor.run())
        # Стартовое сообщение через 5 секунд
        asyncio.create_task(_delayed_startup())

    app = Application.builder().token(tg.token).post_init(_post_init).build()

    # Регистрируем команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("runs", cmd_runs))

    # Регистрируем обработчик ошибок
    app.add_error_handler(error_handler)

    logger.info("Запуск polling-бота...")
    print(f"Лог: {LOG_FILE}")
    print("Для остановки: kill $(pgrep -f tgbot.py)")

    try:
        app.run_polling(
            allowed_updates=["message"],
            close_loop=False,
        )
    except KeyboardInterrupt:
        logger.info("Получен SIGINT, остановка...")
    finally:
        monitor.stop()
        logger.info("tgbot остановлен")
        # Пробуем отправить сообщение об остановке
        loop.run_until_complete(notifier.send("🛑 *tgbot остановлен*"))


if __name__ == "__main__":
    main()
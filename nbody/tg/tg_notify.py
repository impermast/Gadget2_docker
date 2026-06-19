#!/usr/bin/env python3
"""
tg_notify.py — чистый модуль-отправитель Telegram-сообщений.

Не знает о симуляциях, state-файлах, run_name.
Просто читает конфиг и шлёт сообщения/фото/файлы в Telegram.

Использование (из Python):
    from tg_notify import TgNotify
    tg = TgNotify()
    tg.send_message("Hello from simulation!")
    tg.send_photo("Snapshot at t=50", "/path/to/plot.png")
"""

import os
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

logger = logging.getLogger("tg_notify")


class ConfigError(Exception):
    pass


class TelegramAPIError(Exception):
    pass


class TgNotify:
    """
    Отправляет сообщения в Telegram через Bot API.
    Конфиг: /nbody/tg/telegram.conf (или переменные окружения).
    """

    CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram.conf")

    def __init__(self, config_path: Optional[str] = None, token: Optional[str] = None,
                 chat_id: Optional[str] = None):
        """
        Приоритет аргументов:
          1. Параметры token/chat_id (если переданы)
          2. Переменные окружения TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID
          3. Файл telegram.conf
        """
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN") or ""
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID") or ""

        if not self.token or not self.chat_id:
            self._load_config(config_path or self.CONFIG_PATH)

        if not self.token:
            raise ConfigError(
                "BOT_TOKEN не задан. Укажите в telegram.conf, "
                "в переменной TELEGRAM_BOT_TOKEN, или передайте token=..."
            )
        if not self.chat_id:
            raise ConfigError(
                "CHAT_ID не задан. Укажите в telegram.conf, "
                "в переменной TELEGRAM_CHAT_ID, или передайте chat_id=..."
            )

        self._api_base = f"https://api.telegram.org/bot{self.token}"
        self._session = None  # ленивая инициализация

    def _load_config(self, path: str) -> None:
        """Читает BOT_TOKEN и CHAT_ID из конфиг-файла (плоский формат KEY=VALUE)."""
        if not os.path.isfile(path):
            return  # нет файла — надеемся на переменные окружения

        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key == "BOT_TOKEN" and not self.token:
                        self.token = val
                    elif key == "CHAT_ID" and not self.chat_id:
                        self.chat_id = val
        except (OSError, IOError) as e:
            raise ConfigError(f"Ошибка чтения {path}: {e}")

    def _build_url(self, method: str) -> str:
        return f"{self._api_base}/{method}"

    def _import_urllib(self):
        """Ленивый импорт urllib (не блокируем импорт модуля)."""
        try:
            from urllib.request import Request, urlopen
            from urllib.parse import urlencode
            from urllib.error import URLError
            return Request, urlopen, urlencode, URLError
        except ImportError:
            raise TelegramAPIError("urllib not available")

    def send_message(self, text: str, parse_mode: str = "Markdown") -> dict:
        """
        Отправить текстовое сообщение в чат.
        parse_mode: 'Markdown' | 'HTML' | None
        Возвращает JSON-ответ от Telegram API.
        """
        Request, urlopen, urlencode, URLError = self._import_urllib()

        data = {
            "chat_id": self.chat_id,
            "text": text,
        }
        if parse_mode:
            data["parse_mode"] = parse_mode

        url = self._build_url("sendMessage")
        payload = urlencode(data).encode("utf-8")

        try:
            req = Request(url, data=payload, method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            with urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        except URLError as e:
            raise TelegramAPIError(f"Ошибка отправки сообщения: {e}")

    def send_photo(self, caption: str, photo_path: str, parse_mode: str = "Markdown") -> dict:
        """
        Отправить фотографию с подписью.
        photo_path: путь к файлу на диске (внутри контейнера).
        """
        try:
            import json as _json
        except ImportError:
            pass

        # Используем multipart/form-data через subprocess + curl как fallback
        # или через requests, если установлен
        try:
            import requests as req
            with open(photo_path, "rb") as f:
                files = {"photo": f}
                data = {
                    "chat_id": self.chat_id,
                    "caption": caption,
                }
                if parse_mode:
                    data["parse_mode"] = parse_mode
                url = self._build_url("sendPhoto")
                resp = req.post(url, data=data, files=files, timeout=60)
                resp.raise_for_status()
                return resp.json()
        except ImportError:
            pass
        except Exception as e:
            raise TelegramAPIError(f"Ошибка отправки фото (requests): {e}")

        # Fallback: urllib с multipart вручную (сложно) — используем send_document
        raise TelegramAPIError(
            "Для отправки фото установите python-telegram-bot или requests: "
            "pip install requests"
        )

    def send_document(self, file_path: str, caption: Optional[str] = None) -> dict:
        """
        Отправить произвольный файл как документ.
        """
        try:
            import requests as req
            with open(file_path, "rb") as f:
                files = {"document": f}
                data = {"chat_id": self.chat_id}
                if caption:
                    data["caption"] = caption
                url = self._build_url("sendDocument")
                resp = req.post(url, data=data, files=files, timeout=60)
                resp.raise_for_status()
                return resp.json()
        except ImportError:
            raise TelegramAPIError(
                "Для отправки файлов установите requests: pip install requests"
            )
        except Exception as e:
            raise TelegramAPIError(f"Ошибка отправки документа: {e}")


if __name__ == "__main__":
    # Простой тест при прямом запуске
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        tg = TgNotify()
    except ConfigError as e:
        print(f"Ошибка конфигурации: {e}")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        result = tg.send_message("✅ *tg_notify.py* работает!", parse_mode="Markdown")
        print("Отправлено:", result[:200] if len(result) > 200 else result)
    else:
        print("tg_notify.py — модуль-отправитель Telegram")
        print("Использование:")
        print("  python3 tg_notify.py --test    # отправить тестовое сообщение")
        print("  from tg_notify import TgNotify # импорт в Python")
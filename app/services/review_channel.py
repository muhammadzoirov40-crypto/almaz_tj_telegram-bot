from __future__ import annotations

import json
import pathlib
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

_PATH = pathlib.Path(__file__).resolve().parents[2] / "review_channel.json"


def get_channel_id() -> Optional[int]:
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    value = data.get("chat_id")
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def set_channel_id(chat_id: int) -> None:
    try:
        _PATH.write_text(
            json.dumps({"chat_id": int(chat_id)}, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Review channel saved chat_id=%s", chat_id)
    except Exception:
        logger.exception("Cannot save review channel chat_id=%s", chat_id)

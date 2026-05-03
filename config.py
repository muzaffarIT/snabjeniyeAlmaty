import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Environment variable {name} is required")
    return val


def _parse_ids(raw: str) -> list[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


# ================== TELEGRAM ==================

BOT_TOKEN = _require("BOT_TOKEN")

# Ответственные за снабжение (Telegram user IDs, через запятую)
ADMIN_IDS = _parse_ids(_require("ADMIN_IDS"))

# Backwards-compatible alias used across the codebase
IZZAT_IDS = ADMIN_IDS

# ID группы снабжения (супергруппа)
GROUP_ID = int(_require("GROUP_ID"))


# ================== POSTGRES ==================

DATABASE_URL = _require("DATABASE_URL")


# ================== ФИЛИАЛЫ ==================

BRANCHES = {
    1: "Маркова",
    2: "Саина",
    3: "Саяхат",
}


# ================== КАТЕГОРИИ СНАБЖЕНИЯ ==================

CATEGORIES = {
    1: "ХОЗЧАСТЬ",
    2: "МЕБЕЛЬ И РЕМОНТ",
    3: "РАСХОДНИКИ И ЗАКУПКИ",
    4: "IT И ТЕХНИКА",
    5: "УЧЕБНЫЕ МАТЕРИАЛЫ",
}


# ================== СРОЧНОСТЬ ==================

URGENCY = {
    "urgent": "СРОЧНО",
    "normal": "ПЛАНОВО",
}

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from config import BRANCHES, CATEGORIES, URGENCY


_CANCEL_ROW = [InlineKeyboardButton(text="❌ Отмена", callback_data="fsm_cancel")]


# ================== МЕНЮ КУРАТОРА ==================

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Создать заявку")],
            [KeyboardButton(text="📄 Заявки моего филиала")],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие…",
    )


# ================== МЕНЮ ОТВЕТСТВЕННОГО ЗА СНАБЖЕНИЕ ==================

def izzat_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Создать заявку")],
            [
                KeyboardButton(text="🆕 Новые"),
                KeyboardButton(text="🔄 В обработке"),
                KeyboardButton(text="✅ Решённые"),
            ],
            [
                KeyboardButton(text="📍 По филиалу"),
                KeyboardButton(text="📦 По категории"),
            ],
            [
                KeyboardButton(text="📊 Экспорт в Excel"),
                KeyboardButton(text="ℹ️ Помощь"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие…",
    )


# ================== INLINE: ПРОПУСТИТЬ МЕДИА ==================

def skip_media_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Без фото / видео", callback_data="skip_media")],
            _CANCEL_ROW,
        ]
    )


# ================== INLINE: ВЫБОР ФИЛИАЛА ==================

def branches_kb(with_cancel: bool = False):
    keyboard = [
        [InlineKeyboardButton(text=name, callback_data=f"branch_{bid}")]
        for bid, name in BRANCHES.items()
    ]
    if with_cancel:
        keyboard.append(_CANCEL_ROW)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== INLINE: ВЫБОР КАТЕГОРИИ ==================

def categories_kb(with_cancel: bool = True):
    keyboard = [
        [InlineKeyboardButton(text=name, callback_data=f"cat_{cid}")]
        for cid, name in CATEGORIES.items()
    ]
    if with_cancel:
        keyboard.append(_CANCEL_ROW)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================== INLINE: СРОЧНОСТЬ ==================

def urgency_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🔴 {URGENCY['urgent']}", callback_data="urgency_urgent")],
            [InlineKeyboardButton(text=f"🔵 {URGENCY['normal']}", callback_data="urgency_normal")],
            _CANCEL_ROW,
        ]
    )


# ================== INLINE: ПОДТВЕРЖДЕНИЕ ==================

def confirm_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_send"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="confirm_cancel"),
            ]
        ]
    )


# ================== INLINE: ФИЛЬТР ПО КАТЕГОРИИ ==================

def filter_categories_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"filter_cat_{cid}")]
            for cid, name in CATEGORIES.items()
        ]
    )


# ================== INLINE: ФИЛЬТР ПО ФИЛИАЛУ ==================

def filter_branches_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"filter_branch_{bid}")]
            for bid, name in BRANCHES.items()
        ]
    )


# ================== INLINE: СТАТУСЫ В ГРУППЕ ==================

def status_kb(req_id: int, status: str):
    if status == "Новая":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Взять в работу", callback_data=f"work_{req_id}")]
            ]
        )

    if status == "В обработке":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Отметить как решённую", callback_data=f"done_{req_id}")]
            ]
        )

    return None

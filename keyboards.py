from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from config import BRANCHES, CATEGORIES, URGENCY


# ================== МЕНЮ АДМИНА / КУРАТОРА ==================

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Создать заявку")],
            [KeyboardButton(text="📄 Заявки моего филиала")]
        ],
        resize_keyboard=True
    )


# ================== МЕНЮ ОТВЕТСТВЕННОГО (ИЗЗАТ) ==================

def izzat_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
             [KeyboardButton(text="➕ Создать заявку")],
            [
                
                KeyboardButton(text="🆕 Новые"),
                KeyboardButton(text="🔄 В обработке"),
                KeyboardButton(text="✅ Решённые")
            ],
            [
                KeyboardButton(text="📍 По филиалу"),
                KeyboardButton(text="📦 По категории")
            ],
            [
                KeyboardButton(text="📊 Экспорт в Excel")
            ]
        ],
        resize_keyboard=True
    )


# ================== INLINE: ПРОПУСТИТЬ МЕДИА ==================

def skip_media_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏭ Пропустить",
                    callback_data="skip_media"
                )
            ]
        ]
    )


# ================== INLINE: ВЫБОР ФИЛИАЛА ==================

def branches_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=name,
                    callback_data=f"branch_{bid}"
                )
            ]
            for bid, name in BRANCHES.items()
        ]
    )


# ================== INLINE: ВЫБОР КАТЕГОРИИ ==================

def categories_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=name,
                    callback_data=f"cat_{cid}"
                )
            ]
            for cid, name in CATEGORIES.items()
        ]
    )


# ================== INLINE: СРОЧНОСТЬ ==================

def urgency_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🔴 {URGENCY['urgent']}",
                    callback_data="urgency_urgent"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🔵 {URGENCY['normal']}",
                    callback_data="urgency_normal"
                )
            ]
        ]
    )


# ================== INLINE: ПОДТВЕРЖДЕНИЕ ==================

def confirm_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Отправить заявку",
                    callback_data="confirm_send"
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="confirm_cancel"
                )
            ]
        ]
    )


# ================== INLINE: СТАТУСЫ В ГРУППЕ ==================

def status_kb(req_id: int, status: str):
    if status == "Новая":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 В обработке",
                        callback_data=f"work_{req_id}"
                    )
                ]
            ]
        )

    if status == "В обработке":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Решено",
                        callback_data=f"done_{req_id}"
                    )
                ]
            ]
        )

    return None

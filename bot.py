import asyncio
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import BOT_TOKEN, IZZAT_IDS, GROUP_ID, BRANCHES, CATEGORIES, URGENCY
from database import (
    set_user_branch,
    get_user_branch,
    add_request,
    update_status,
    get_requests_by_branch,
    get_requests_by_status,
    get_all_requests,
    get_requests_by_category
)

from states import RequestFSM
from keyboards import (
    admin_menu,
    skip_media_kb,
    izzat_menu,
    branches_kb,
    categories_kb,
    urgency_kb,
    status_kb,
    confirm_kb
)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ================== START ==================
@dp.message(Command("start"))
async def start(message: Message):
    # 🔴 ИЗЗАТ — НИКОГДА НЕ ВЫБИРАЕТ ФИЛИАЛ
    if message.from_user.id in IZZAT_IDS:
        await message.answer(
            "🛠 <b> Управление снабжением </b>",
            reply_markup=izzat_menu(),
            parse_mode="HTML"

        )

            
    
        return

    branch_id = get_user_branch(message.from_user.id)

    if branch_id is None:
        await message.answer(
            "Пожалуйста, выберите ваш филиал:",
            reply_markup=branches_kb()
        )
        return

    await message.answer(
        "📋 Меню снабжения",
        reply_markup=admin_menu()
    )


                  
# ================== ВЫБОР ФИЛИАЛА ==================

@dp.callback_query(F.data.startswith("branch_"), ~F.from_user.id.in_(IZZAT_IDS))
async def admin_choose_branch(call: CallbackQuery):
    branch_id = int(call.data.split("_")[1])

    set_user_branch(call.from_user.id, branch_id)

    await call.message.edit_reply_markup()
    await call.message.answer(
        f"Филиал «{BRANCHES[branch_id]}» сохранён ✅",
        reply_markup=admin_menu()
    )
@dp.callback_query(RequestFSM.branch, F.data.startswith("branch_"))
async def izzat_choose_branch(call: CallbackQuery, state: FSMContext):
    branch_id = int(call.data.split("_")[1])

    await call.message.edit_reply_markup()

    await state.update_data(branch_id=branch_id)

    await call.message.answer(
        "📦 <b>Выберите категорию снабжения:</b>",
        reply_markup=categories_kb(),
        parse_mode="HTML"
    )
    await state.set_state(RequestFSM.category)


# ================== СОЗДАНИЕ ЗАЯВКИ ==================
@dp.message(F.text == "➕ Создать заявку")
async def new_request(message: Message, state: FSMContext):
    await state.clear()

    # ИЗЗАТ — ВСЕГДА СПРАШИВАЕМ ФИЛИАЛ
    if message.from_user.id in IZZAT_IDS:
        await message.answer(
            "📍 <b>Выберите филиал для заявки:</b>",
            reply_markup=branches_kb(),
            parse_mode="HTML"
        )
        await state.set_state(RequestFSM.branch)
        return

    # КУРАТОР
    branch_id = get_user_branch(message.from_user.id)

    if branch_id is None:
        await message.answer(
            "Пожалуйста, выберите ваш филиал:",
            reply_markup=branches_kb()
        )
        return

    await message.answer(
        "📦 <b>Выберите категорию снабжения:</b>",
        reply_markup=categories_kb(),
        parse_mode="HTML"
    )
    await state.set_state(RequestFSM.category)


# ================== КАТЕГОРИЯ ==================

@dp.callback_query(RequestFSM.category, F.data.startswith("cat_"))
async def choose_category(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()  # ⬅️ УБРАЛИ КНОПКИ КАТЕГОРИЙ

    await state.update_data(category_id=int(call.data.split("_")[1]))

    await call.message.answer(
      " 📝 Кратко опишите проблему:",
        parse_mode="HTML"
    )
    await state.set_state(RequestFSM.description)

# ================== ОПИСАНИЕ ==================
@dp.message(RequestFSM.description)
async def get_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)

    await message.answer(
    "📸 <b>Прикрепите фото или видео (если есть)</b>\n\n"
    "Если файлов нет — нажмите кнопку ниже ⬇️",
    reply_markup=skip_media_kb(),
    parse_mode="HTML"
)


    await state.set_state(RequestFSM.media)




# ================== МЕДИА ==================
@dp.message(RequestFSM.media, F.content_type.in_({"photo", "video"}))
async def get_media(message: Message, state: FSMContext):
    if message.photo:
        media = {"type": "photo", "file_id": message.photo[-1].file_id}
    else:
        media = {"type": "video", "file_id": message.video.file_id}

    await state.update_data(media=media)

    await message.answer(
        "⏱ Укажите срочность:",
        reply_markup=urgency_kb()
    )
    await state.set_state(RequestFSM.urgency)


@dp.callback_query(RequestFSM.media, F.data == "skip_media")
async def skip_media(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()  # ⬅️ УБРАЛИ «ПРОПУСТИТЬ»

    await state.update_data(media=None)

    await call.message.answer(
        "⏱ <b>Укажите срочность:</b>",
        reply_markup=urgency_kb(),
        parse_mode="HTML"
    )
    await state.set_state(RequestFSM.urgency)



# ================== СРОЧНОСТЬ + ПРОВЕРКА ==================
@dp.callback_query(RequestFSM.urgency, F.data.startswith("urgency_"))
async def choose_urgency(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup() 
    urgency = call.data.split("_")[1]
    await state.update_data(urgency=urgency)

    data = await state.get_data()

    branch_id = data.get("branch_id") or get_user_branch(call.from_user.id)


    preview = (
        "📋 <b>ПРОВЕРЬТЕ ЗАЯВКУ</b>\n\n"
        f"📍 <b>Филиал:</b> {BRANCHES[branch_id]}\n"
        f"📦 <b>Категория:</b> {CATEGORIES[data['category_id']]}\n"
        f"⏱ <b>Срочность:</b> {URGENCY[urgency]}\n\n"
        f"📝 <b>Описание:</b>\n{data['description']}"
    )

    media = data.get("media")

    if media:
        if media["type"] == "photo":
            await call.message.answer_photo(
                media["file_id"],
                caption=preview,
                reply_markup=confirm_kb(),
                parse_mode="HTML"
            )
        else:
            await call.message.answer_video(
                media["file_id"],
                caption=preview,
                reply_markup=confirm_kb(),
                parse_mode="HTML"
            )
    else:
        await call.message.answer(
            preview,
            reply_markup=confirm_kb(),
            parse_mode="HTML"
        )

    await state.set_state(RequestFSM.confirm)


# ================== ПОДТВЕРЖДЕНИЕ ==================
@dp.callback_query(RequestFSM.confirm, F.data == "confirm_send")
async def confirm_send(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    branch_id = data.get("branch_id") or get_user_branch(call.from_user.id)


    created = datetime.now().isoformat()

    req_id = add_request((
        call.from_user.id,
        branch_id,
        data["category_id"],
        data["urgency"],
        data["description"],
        "Новая",
        created,
        None
    ))

    branch_tag = f"#{BRANCHES[branch_id]}"
    category_tag = f"#{CATEGORIES[data['category_id']].split()[0]}"
    urgency_tag = "#Срочно" if data["urgency"] == "urgent" else "#Планово"

    text = f"""🆕 <b>ЗАЯВКА №{req_id}</b>

📍 <b>Филиал:</b> {BRANCHES[branch_id]}
📦 <b>Категория:</b> {CATEGORIES[data['category_id']]}
⏱ <b>Срочность:</b> {URGENCY[data['urgency']]}

📝 <b>Описание:</b>
{data['description']}

{branch_tag}
{category_tag}
{urgency_tag}
"""

    media = data.get("media")

    if media:
        if media["type"] == "photo":
            await bot.send_photo(
                chat_id=GROUP_ID,
                photo=media["file_id"],
                caption=text,
                parse_mode="HTML",
                reply_markup=status_kb(req_id, "Новая")
            )
        else:
            await bot.send_video(
                chat_id=GROUP_ID,
                video=media["file_id"],
                caption=text,
                parse_mode="HTML",
                reply_markup=status_kb(req_id, "Новая")
            )
    else:
        await bot.send_message(
            chat_id=GROUP_ID,
            text=text,
            parse_mode="HTML",
            reply_markup=status_kb(req_id, "Новая")
        )

    menu = izzat_menu() if call.from_user.id in IZZAT_IDS else admin_menu()

    await call.message.answer(
    "✅ <b>Заявка отправлена</b>",
    reply_markup=menu,
    parse_mode="HTML"
    )
    await state.clear()



@dp.callback_query(RequestFSM.confirm, F.data == "confirm_cancel")
async def confirm_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()

    await call.message.edit_reply_markup()  # убрать кнопки подтверждения

    menu = izzat_menu() if call.from_user.id in IZZAT_IDS else admin_menu()

    await call.message.answer(
        "❌ <b>Заявка отменена</b>",
        reply_markup=menu,
        parse_mode="HTML"
    )


# ================== ПРОСМОТР ДЛЯ АДМИНОВ ==================

def status_emoji(status: str) -> str:
    if status == "Новая":
        return "🟡"
    if status == "В обработке":
        return "🔄"
    if status == "Решено":
        return "🟢"
    return "⚪️"


@dp.message(F.text == "📄 Заявки моего филиала")
async def my_branch_requests(message: Message):
    branch_id = get_user_branch(message.from_user.id)
    rows = get_requests_by_branch(branch_id)

    if not rows:
        await message.answer(
            "📄 <b>Заявок нет</b>",
            parse_mode="HTML"
        )
        return

    text = "📄 <b>Заявки вашего филиала</b>\n\n"

    for r in rows:
        req_id = r[0]
        description = r[1][:60]
        status = r[2]

        text += (
            f"🧾 <b>Заявка №{req_id}</b>\n"
            f"📝 {description}…\n"
            f"{status_emoji(status)} <b>Статус:</b> {status}\n"
            f"────────────\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )
@dp.message(F.text == "🆕 Новые")
async def izzat_new(message: Message):
    if message.from_user.id not in IZZAT_IDS:
        return

    rows = get_requests_by_status("Новая")

    if not rows:
        await message.answer(
            "🆕 <b>Новых заявок нет</b>",
            parse_mode="HTML"
        )
        return

    text = "🆕 <b>Новые заявки</b>\n\n"

    for r in rows:
        req_id = r[0]
        description = r[1][:60]
        branch = BRANCHES[r[2]]

        text += (
            f"🧾 <b>Заявка №{req_id}</b>\n"
            f"📝 {description}…\n"
            f"📍 {branch}\n"
            f"🟡 <b>Статус:</b> Новая\n"
            f"────────────\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )

@dp.message(F.text == "🔄 В обработке")
async def izzat_work(message: Message):
    if message.from_user.id not in IZZAT_IDS:
        return

    rows = get_requests_by_status("В обработке")

    if not rows:
        await message.answer(
            "🔄 <b>Нет заявок в обработке</b>",
            parse_mode="HTML"
        )
        return

    text = "🔄 <b>Заявки в обработке</b>\n\n"

    for r in rows:
        req_id = r[0]
        description = r[1][:60]
        branch = BRANCHES[r[2]]

        text += (
            f"🧾 <b>Заявка №{req_id}</b>\n"
            f"📝 {description}…\n"
            f"📍 {branch}\n"
            f"🔄 <b>Статус:</b> В обработке\n"
            f"────────────\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )

@dp.message(F.text == "✅ Решённые")
async def izzat_done(message: Message):
    if message.from_user.id not in IZZAT_IDS:
        return

    rows = get_requests_by_status("Решено")

    if not rows:
        await message.answer(
            "✅ <b>Решённых заявок нет</b>",
            parse_mode="HTML"
        )
        return

    text = "✅ <b>Решённые заявки</b>\n\n"

    for r in rows:
        req_id = r[0]
        description = r[1][:60]
        branch = BRANCHES[r[2]]

        text += (
            f"🧾 <b>Заявка №{req_id}</b>\n"
            f"📝 {description}…\n"
            f"📍 {branch}\n"
            f"🟢 <b>Статус:</b> Решено\n"
            f"────────────\n"
        )

    await message.answer(
        text,
        parse_mode="HTML"
    )

@dp.message(F.text == "📦 По категории")
async def search_by_category(message: Message):
    await message.answer(
        "Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=name,
                        callback_data=f"filter_cat_{cid}"
                    )
                ]
                for cid, name in CATEGORIES.items()
            ]
        ),
       parse_mode="HTML"

    )


@dp.callback_query(F.data.startswith("filter_cat_"))
async def filter_category(call: CallbackQuery):
    cat_id = int(call.data.split("_")[2])
    rows = get_requests_by_category(cat_id)

    if not rows:
        await call.message.answer("📦 Заявок нет", parse_mode="HTML")
        return

    text = f"📦 Категория: {CATEGORIES[cat_id]}\n\n"

    for r in rows:
        req_id = r[0]
        description = r[1][:50]
        status = r[2]

        text += (
            f"🧾 <b>Заявка №{req_id}</b>\n"
    f"📝 {description}…\n"
    f"{status_emoji(status)} <b>Статус:</b> {status}\n\n"

        )

    await call.message.answer(text, parse_mode="HTML")



@dp.message(F.text == "📊 Экспорт в Excel")
async def export_excel(message: Message):
    if message.from_user.id not in IZZAT_IDS:
        return

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active

    ws.append([
    "ID", "Филиал", "Категория",
    "Срочность", "Описание", "Статус", "Создано"
    ])


    for r in get_all_requests():
        ws.append([
            r[0],
            BRANCHES.get(r[2], "—"),
            CATEGORIES.get(r[3], "—"),
            URGENCY.get(r[4], "—"),
            r[5],
            r[6],
            r[7]
        ])

    file_path = "export.xlsx"
    wb.save(file_path)

    await message.answer_document(
        FSInputFile(file_path),
        caption="📊 Экспорт заявок"
    )



@dp.message(F.text == "📍 По филиалу")
async def search_by_branch(message: Message):
    await message.answer(
        "Выберите филиал:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=name,
                        callback_data=f"filter_branch_{bid}"
                    )
                ]
                for bid, name in BRANCHES.items()
            ]
        ),
        parse_mode="HTML"

    )
@dp.callback_query(F.data.startswith("filter_branch_"))
async def filter_branch(call: CallbackQuery):
    branch_id = int(call.data.split("_")[2])
    rows = get_requests_by_branch(branch_id)

    if not rows:
        await call.message.answer(
            "📍 <b>Заявок нет</b>",
            parse_mode="HTML"
        )
        return

    text = f"📍 <b>Филиал:</b> {BRANCHES[branch_id]}\n\n"

    for r in rows:
        req_id = r[0]
        description = r[1][:60]
        status = r[2]

        text += (
            f"🧾 <b>Заявка №{req_id}</b>\n"
            f"📝 {description}…\n"
            f"{status_emoji(status)} <b>Статус:</b> {status}\n"
            f"────────────\n"
        )

    await call.message.answer(
        text,
        parse_mode="HTML"
    )

# ================== СТАТУСЫ В ГРУППЕ ==================

@dp.callback_query(F.data.startswith(("work_", "done_")))
async def change_status(call: CallbackQuery):
    if call.from_user.id not in IZZAT_IDS: 
        return

    action, req_id = call.data.split("_")
    status = "В обработке" if action == "work" else "Решено"

    update_status(int(req_id), status)

    import re

    base_text = call.message.text or call.message.caption or ""

# убираем старую строку статуса, если есть
    base_text = re.sub(r"\n\nСтатус:.*", "", base_text)

    new_text = base_text + f"\n\n<b>Статус:</b> {status}"



# ЕСЛИ ЭТО ФОТО / ВИДЕО → edit_caption
    if call.message.caption is not None:
        await call.message.edit_caption(
            caption=new_text,
            reply_markup=status_kb(int(req_id), status),
            parse_mode="HTML"

        )
    else:
        await call.message.edit_text(
        new_text,
        reply_markup=status_kb(int(req_id), status),
       parse_mode="HTML"

    )



# ================== RUN ==================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

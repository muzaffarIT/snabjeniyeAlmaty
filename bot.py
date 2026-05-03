import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    Message,
)

from config import BOT_TOKEN, IZZAT_IDS, GROUP_ID, BRANCHES, CATEGORIES, URGENCY
from database import (
    add_request,
    get_all_requests,
    get_request_author,
    get_requests_by_branch,
    get_requests_by_category,
    get_requests_by_status,
    get_user_branch,
    set_user_branch,
    update_status,
)
from keyboards import (
    admin_menu,
    branches_kb,
    categories_kb,
    confirm_kb,
    filter_branches_kb,
    filter_categories_kb,
    izzat_menu,
    skip_media_kb,
    status_kb,
    urgency_kb,
)
from states import RequestFSM

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

DESCRIPTION_MAX_LEN = 3500
LIST_PREVIEW_LEN = 80


def is_admin(user_id: int) -> bool:
    return user_id in IZZAT_IDS


def main_menu_for(user_id: int):
    return izzat_menu() if is_admin(user_id) else admin_menu()


def status_emoji(status: str) -> str:
    return {
        "Новая": "🟡",
        "В обработке": "🔄",
        "Решено": "🟢",
    }.get(status, "⚪️")


def human_age(created_at: str) -> str:
    """'2 ч назад', 'вчера', '3 дн назад'."""
    try:
        dt = datetime.fromisoformat(created_at)
    except (TypeError, ValueError):
        return ""
    delta = datetime.now() - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "только что"
    if seconds < 3600:
        return f"{seconds // 60} мин назад"
    if seconds < 86400:
        return f"{seconds // 3600} ч назад"
    days = seconds // 86400
    if days == 1:
        return "вчера"
    return f"{days} дн назад"


# ================== /START ==================

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    if is_admin(message.from_user.id):
        await message.answer(
            "👋 <b>Добро пожаловать в систему снабжения!</b>\n\n"
            "Вы вошли как <b>ответственный за снабжение</b>.\n"
            "Здесь вы видите все заявки филиалов, можете брать их в работу "
            "и закрывать.\n\n"
            "📌 Подсказка: команда /help — описание всех кнопок.\n"
            "Выберите действие в меню ниже ⬇️",
            reply_markup=izzat_menu(),
            parse_mode="HTML",
        )
        return

    branch_id = get_user_branch(message.from_user.id)

    if branch_id is None:
        await message.answer(
            "👋 <b>Здравствуйте!</b>\n\n"
            "Это бот для подачи заявок снабжения по филиалам Алматы.\n\n"
            "Для начала выберите свой филиал — он сохранится, "
            "и в дальнейшем все ваши заявки будут автоматически "
            "привязываться к нему.",
            reply_markup=branches_kb(),
            parse_mode="HTML",
        )
        return

    await message.answer(
        f"📋 <b>Главное меню</b>\n\n"
        f"📍 Ваш филиал: <b>{BRANCHES[branch_id]}</b>\n\n"
        "Чтобы создать заявку — нажмите «➕ Создать заявку».\n"
        "Чтобы посмотреть свои заявки — «📄 Заявки моего филиала».",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )


# ================== /HELP ==================

@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    if is_admin(message.from_user.id):
        text = (
            "ℹ️ <b>Помощь — режим ответственного</b>\n\n"
            "<b>➕ Создать заявку</b> — оформить заявку от любого филиала.\n"
            "<b>🆕 Новые</b> — заявки, которые ещё не взяты в работу.\n"
            "<b>🔄 В обработке</b> — заявки, которые уже решаются.\n"
            "<b>✅ Решённые</b> — закрытые заявки.\n"
            "<b>📍 По филиалу</b> — фильтр по филиалу.\n"
            "<b>📦 По категории</b> — фильтр по категории.\n"
            "<b>📊 Экспорт в Excel</b> — все заявки одним файлом.\n\n"
            "<b>В группе</b> под каждой новой заявкой есть кнопка "
            "«🔄 Взять в работу». После — «✅ Отметить как решённую».\n"
            "Автор заявки получит уведомление о смене статуса автоматически.\n\n"
            "Команды: /start, /menu, /id, /cancel, /help"
        )
    else:
        text = (
            "ℹ️ <b>Помощь</b>\n\n"
            "<b>➕ Создать заявку</b> — оформить новую заявку:\n"
            "  1. Категория\n"
            "  2. Описание (что нужно)\n"
            "  3. Фото / видео (по желанию)\n"
            "  4. Срочность\n"
            "  5. Подтверждение\n\n"
            "<b>📄 Заявки моего филиала</b> — статус ваших заявок.\n\n"
            "Когда заявку возьмут в работу или закроют — придёт уведомление.\n\n"
            "Команды: /start, /menu, /id, /cancel, /help"
        )
    await message.answer(text, parse_mode="HTML")


# ================== /ID ==================

@dp.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(
        f"🆔 Ваш Telegram ID: <code>{message.from_user.id}</code>\n\n"
        "💡 Сохраните его — этот ID нужен, чтобы вас добавили "
        "в список ответственных за снабжение.",
        parse_mode="HTML",
    )


# ================== /MENU ==================

@dp.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📋 Главное меню",
        reply_markup=main_menu_for(message.from_user.id),
    )


# ================== /CANCEL ==================

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer(
            "Сейчас нечего отменять — вы в главном меню.",
            reply_markup=main_menu_for(message.from_user.id),
        )
        return
    await state.clear()
    await message.answer(
        "❌ Создание заявки отменено.\nВозвращаю в главное меню.",
        reply_markup=main_menu_for(message.from_user.id),
    )


@dp.callback_query(F.data == "fsm_cancel")
async def cb_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_reply_markup()
    await call.message.answer(
        "❌ Создание заявки отменено.\nВозвращаю в главное меню.",
        reply_markup=main_menu_for(call.from_user.id),
    )
    await call.answer()


# ================== ВЫБОР ФИЛИАЛА (КУРАТОР, ВНЕ FSM) ==================

@dp.callback_query(F.data.startswith("branch_"), ~F.from_user.id.in_(IZZAT_IDS))
async def curator_choose_branch(call: CallbackQuery, state: FSMContext):
    if await state.get_state() is not None:
        return
    branch_id = int(call.data.split("_")[1])
    set_user_branch(call.from_user.id, branch_id)
    await call.message.edit_reply_markup()
    await call.message.answer(
        f"✅ Ваш филиал сохранён: <b>{BRANCHES[branch_id]}</b>\n\n"
        "Теперь вы можете создавать заявки и отслеживать их статус.",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )
    await call.answer()


# ================== ВЫБОР ФИЛИАЛА (АДМИН, ВНУТРИ FSM) ==================

@dp.callback_query(RequestFSM.branch, F.data.startswith("branch_"))
async def izzat_choose_branch(call: CallbackQuery, state: FSMContext):
    branch_id = int(call.data.split("_")[1])
    await call.message.edit_reply_markup()
    await state.update_data(branch_id=branch_id)
    await call.message.answer(
        f"📍 Филиал: <b>{BRANCHES[branch_id]}</b>\n\n"
        "📦 <b>Шаг 1 из 4 — Категория</b>\n"
        "К чему относится заявка?",
        reply_markup=categories_kb(),
        parse_mode="HTML",
    )
    await state.set_state(RequestFSM.category)
    await call.answer()


# ================== СОЗДАНИЕ ЗАЯВКИ ==================

@dp.message(F.text == "➕ Создать заявку")
async def new_request(message: Message, state: FSMContext):
    await state.clear()

    if is_admin(message.from_user.id):
        await message.answer(
            "📍 <b>Шаг 0 из 4 — Филиал</b>\n"
            "Для какого филиала создаём заявку?",
            reply_markup=branches_kb(with_cancel=True),
            parse_mode="HTML",
        )
        await state.set_state(RequestFSM.branch)
        return

    branch_id = get_user_branch(message.from_user.id)

    if branch_id is None:
        await message.answer(
            "Сначала выберите ваш филиал ⬇️",
            reply_markup=branches_kb(),
        )
        return

    await message.answer(
        f"📍 Филиал: <b>{BRANCHES[branch_id]}</b>\n\n"
        "📦 <b>Шаг 1 из 4 — Категория</b>\n"
        "К чему относится заявка?",
        reply_markup=categories_kb(),
        parse_mode="HTML",
    )
    await state.set_state(RequestFSM.category)


# ================== КАТЕГОРИЯ ==================

@dp.callback_query(RequestFSM.category, F.data.startswith("cat_"))
async def choose_category(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await state.update_data(category_id=int(call.data.split("_")[1]))
    await call.message.answer(
        "📝 <b>Шаг 2 из 4 — Описание</b>\n\n"
        "Опишите проблему или что нужно закупить.\n"
        "Чем подробнее — тем быстрее решим 🙌\n\n"
        "<i>Чтобы отменить — /cancel</i>",
        parse_mode="HTML",
    )
    await state.set_state(RequestFSM.description)
    await call.answer()


# ================== ОПИСАНИЕ ==================

@dp.message(RequestFSM.description)
async def get_description(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer(
            "❗ Пожалуйста, отправьте <b>текстовое</b> описание заявки.\n"
            "Фото и видео можно будет прикрепить на следующем шаге.",
            parse_mode="HTML",
        )
        return
    if len(text) > DESCRIPTION_MAX_LEN:
        await message.answer(
            f"❗ Описание слишком длинное ({len(text)} символов).\n"
            f"Сократите до {DESCRIPTION_MAX_LEN} символов и пришлите снова."
        )
        return

    await state.update_data(description=text)
    await message.answer(
        "📸 <b>Шаг 3 из 4 — Фото / видео</b>\n\n"
        "Прикрепите фото или короткое видео, если это поможет понять задачу.\n"
        "Если файлов нет — нажмите «⏭ Без фото / видео».",
        reply_markup=skip_media_kb(),
        parse_mode="HTML",
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
        "⏱ <b>Шаг 4 из 4 — Срочность</b>\n\n"
        "🔴 <b>СРОЧНО</b> — нужно решить как можно скорее\n"
        "🔵 <b>ПЛАНОВО</b> — можно решить в обычном порядке",
        reply_markup=urgency_kb(),
        parse_mode="HTML",
    )
    await state.set_state(RequestFSM.urgency)


@dp.message(RequestFSM.media)
async def media_wrong_type(message: Message):
    await message.answer(
        "❗ Здесь нужно прикрепить <b>фото</b> или <b>видео</b>.\n"
        "Если ничего не нужно — нажмите «⏭ Без фото / видео».",
        reply_markup=skip_media_kb(),
        parse_mode="HTML",
    )


@dp.callback_query(RequestFSM.media, F.data == "skip_media")
async def skip_media(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    await state.update_data(media=None)
    await call.message.answer(
        "⏱ <b>Шаг 4 из 4 — Срочность</b>\n\n"
        "🔴 <b>СРОЧНО</b> — нужно решить как можно скорее\n"
        "🔵 <b>ПЛАНОВО</b> — можно решить в обычном порядке",
        reply_markup=urgency_kb(),
        parse_mode="HTML",
    )
    await state.set_state(RequestFSM.urgency)
    await call.answer()


# ================== СРОЧНОСТЬ + ПРОВЕРКА ==================

@dp.callback_query(RequestFSM.urgency, F.data.startswith("urgency_"))
async def choose_urgency(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup()
    urgency = call.data.split("_")[1]
    await state.update_data(urgency=urgency)

    data = await state.get_data()
    branch_id = data.get("branch_id") or get_user_branch(call.from_user.id)

    preview = (
        "📋 <b>ПРОВЕРКА ЗАЯВКИ</b>\n\n"
        f"📍 <b>Филиал:</b> {BRANCHES[branch_id]}\n"
        f"📦 <b>Категория:</b> {CATEGORIES[data['category_id']]}\n"
        f"⏱ <b>Срочность:</b> {URGENCY[urgency]}\n\n"
        f"📝 <b>Описание:</b>\n{data['description']}\n\n"
        "Всё верно? Нажмите «✅ Отправить».\n"
        "Если что-то не так — «❌ Отменить» и создайте заново."
    )

    media = data.get("media")
    if media:
        if media["type"] == "photo":
            await call.message.answer_photo(
                media["file_id"],
                caption=preview,
                reply_markup=confirm_kb(),
                parse_mode="HTML",
            )
        else:
            await call.message.answer_video(
                media["file_id"],
                caption=preview,
                reply_markup=confirm_kb(),
                parse_mode="HTML",
            )
    else:
        await call.message.answer(preview, reply_markup=confirm_kb(), parse_mode="HTML")

    await state.set_state(RequestFSM.confirm)
    await call.answer()


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
        None,
    ))

    branch_tag = f"#{BRANCHES[branch_id].replace(' ', '_')}"
    category_tag = f"#{CATEGORIES[data['category_id']].split()[0]}"
    urgency_tag = "#Срочно" if data["urgency"] == "urgent" else "#Планово"

    text = (
        f"🆕 <b>ЗАЯВКА №{req_id}</b>\n\n"
        f"📍 <b>Филиал:</b> {BRANCHES[branch_id]}\n"
        f"📦 <b>Категория:</b> {CATEGORIES[data['category_id']]}\n"
        f"⏱ <b>Срочность:</b> {URGENCY[data['urgency']]}\n\n"
        f"📝 <b>Описание:</b>\n{data['description']}\n\n"
        f"{branch_tag} {category_tag} {urgency_tag}"
    )

    media = data.get("media")
    try:
        if media:
            if media["type"] == "photo":
                await bot.send_photo(
                    chat_id=GROUP_ID,
                    photo=media["file_id"],
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=status_kb(req_id, "Новая"),
                )
            else:
                await bot.send_video(
                    chat_id=GROUP_ID,
                    video=media["file_id"],
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=status_kb(req_id, "Новая"),
                )
        else:
            await bot.send_message(
                chat_id=GROUP_ID,
                text=text,
                parse_mode="HTML",
                reply_markup=status_kb(req_id, "Новая"),
            )
    except Exception as e:
        await call.message.answer(
            f"⚠️ Заявка №{req_id} сохранена, но не удалось отправить её в группу:\n"
            f"<code>{e}</code>\n\n"
            "Проверьте, что бот добавлен в группу как админ.",
            parse_mode="HTML",
        )

    await call.message.answer(
        f"✅ <b>Заявка №{req_id} отправлена!</b>\n\n"
        "Она уже у ответственного за снабжение.\n"
        "Как только статус изменится — придёт уведомление 🔔",
        reply_markup=main_menu_for(call.from_user.id),
        parse_mode="HTML",
    )
    await state.clear()
    await call.answer()


@dp.callback_query(RequestFSM.confirm, F.data == "confirm_cancel")
async def confirm_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_reply_markup()
    await call.message.answer(
        "❌ Создание заявки отменено.\nВы можете начать заново в любой момент.",
        reply_markup=main_menu_for(call.from_user.id),
        parse_mode="HTML",
    )
    await call.answer()


# ================== ПРОСМОТР: КУРАТОР ==================

@dp.message(F.text == "📄 Заявки моего филиала")
async def my_branch_requests(message: Message):
    branch_id = get_user_branch(message.from_user.id)

    if branch_id is None:
        await message.answer(
            "Сначала выберите ваш филиал ⬇️",
            reply_markup=branches_kb(),
        )
        return

    rows = get_requests_by_branch(branch_id)
    if not rows:
        await message.answer(
            "📭 <b>Пока заявок нет</b>\n\n"
            "Создайте первую через «➕ Создать заявку».",
            parse_mode="HTML",
        )
        return

    text = (
        f"📄 <b>Заявки филиала «{BRANCHES[branch_id]}»</b>\n"
        f"Всего: <b>{len(rows)}</b>\n\n"
    )
    for r in rows:
        req_id, description, status, created_at = r
        text += (
            f"🧾 <b>№{req_id}</b> · {status_emoji(status)} {status} · {human_age(created_at)}\n"
            f"📝 {description[:LIST_PREVIEW_LEN]}{'…' if len(description) > LIST_PREVIEW_LEN else ''}\n"
            f"────────────\n"
        )
    await message.answer(text, parse_mode="HTML")


# ================== ПРОСМОТР: АДМИН ПО СТАТУСУ ==================

async def _list_by_status(message: Message, status: str, header: str, empty: str):
    if not is_admin(message.from_user.id):
        return
    rows = get_requests_by_status(status)
    if not rows:
        await message.answer(empty, parse_mode="HTML")
        return

    text = f"{header}\nВсего: <b>{len(rows)}</b>\n\n"
    for r in rows:
        req_id, description, branch_id, created_at = r
        text += (
            f"🧾 <b>№{req_id}</b> · 📍 {BRANCHES.get(branch_id, '—')} · {human_age(created_at)}\n"
            f"📝 {description[:LIST_PREVIEW_LEN]}{'…' if len(description) > LIST_PREVIEW_LEN else ''}\n"
            f"────────────\n"
        )
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "🆕 Новые")
async def izzat_new(message: Message):
    await _list_by_status(
        message,
        "Новая",
        "🆕 <b>Новые заявки</b>",
        "🆕 <b>Новых заявок нет</b>\nВсё под контролем 👌",
    )


@dp.message(F.text == "🔄 В обработке")
async def izzat_work(message: Message):
    await _list_by_status(
        message,
        "В обработке",
        "🔄 <b>Заявки в работе</b>",
        "🔄 <b>В работе ничего нет</b>",
    )


@dp.message(F.text == "✅ Решённые")
async def izzat_done(message: Message):
    await _list_by_status(
        message,
        "Решено",
        "✅ <b>Решённые заявки</b>",
        "✅ <b>Решённых заявок пока нет</b>",
    )


# ================== ПРОСМОТР: ФИЛЬТРЫ ==================

@dp.message(F.text == "📦 По категории")
async def search_by_category(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "📦 <b>Выберите категорию для просмотра:</b>",
        reply_markup=filter_categories_kb(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("filter_cat_"))
async def filter_category(call: CallbackQuery):
    cat_id = int(call.data.split("_")[2])
    rows = get_requests_by_category(cat_id)
    if not rows:
        await call.message.answer(
            f"📦 <b>Категория «{CATEGORIES[cat_id]}»</b>\nЗаявок нет.",
            parse_mode="HTML",
        )
        await call.answer()
        return

    text = (
        f"📦 <b>Категория: {CATEGORIES[cat_id]}</b>\n"
        f"Всего: <b>{len(rows)}</b>\n\n"
    )
    for r in rows:
        req_id, description, status, created_at = r
        text += (
            f"🧾 <b>№{req_id}</b> · {status_emoji(status)} {status} · {human_age(created_at)}\n"
            f"📝 {description[:LIST_PREVIEW_LEN]}{'…' if len(description) > LIST_PREVIEW_LEN else ''}\n\n"
        )
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()


@dp.message(F.text == "📍 По филиалу")
async def search_by_branch(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "📍 <b>Выберите филиал для просмотра:</b>",
        reply_markup=filter_branches_kb(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("filter_branch_"))
async def filter_branch(call: CallbackQuery):
    branch_id = int(call.data.split("_")[2])
    rows = get_requests_by_branch(branch_id)
    if not rows:
        await call.message.answer(
            f"📍 <b>Филиал «{BRANCHES[branch_id]}»</b>\nЗаявок нет.",
            parse_mode="HTML",
        )
        await call.answer()
        return

    text = (
        f"📍 <b>Филиал: {BRANCHES[branch_id]}</b>\n"
        f"Всего: <b>{len(rows)}</b>\n\n"
    )
    for r in rows:
        req_id, description, status, created_at = r
        text += (
            f"🧾 <b>№{req_id}</b> · {status_emoji(status)} {status} · {human_age(created_at)}\n"
            f"📝 {description[:LIST_PREVIEW_LEN]}{'…' if len(description) > LIST_PREVIEW_LEN else ''}\n"
            f"────────────\n"
        )
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()


# ================== ЭКСПОРТ ==================

@dp.message(F.text == "📊 Экспорт в Excel")
async def export_excel(message: Message):
    if not is_admin(message.from_user.id):
        return

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Заявки"
    ws.append(["ID", "Филиал", "Категория", "Срочность", "Описание", "Статус", "Создано"])

    for r in get_all_requests():
        ws.append([
            r[0],
            BRANCHES.get(r[2], "—"),
            CATEGORIES.get(r[3], "—"),
            URGENCY.get(r[4], "—"),
            r[5],
            r[6],
            r[7],
        ])

    file_path = "export.xlsx"
    wb.save(file_path)
    await message.answer_document(FSInputFile(file_path), caption="📊 Экспорт всех заявок")


# ================== СМЕНА СТАТУСА В ГРУППЕ ==================

@dp.callback_query(F.data.startswith(("work_", "done_")))
async def change_status(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Только для ответственных за снабжение", show_alert=True)
        return

    action, req_id = call.data.split("_")
    req_id = int(req_id)
    status = "В обработке" if action == "work" else "Решено"

    update_status(req_id, status)

    import re
    base_text = call.message.text or call.message.caption or ""
    base_text = re.sub(r"\n\n<b>Статус:</b>.*", "", base_text, flags=re.DOTALL)
    base_text = re.sub(r"\n\nСтатус:.*", "", base_text, flags=re.DOTALL)

    actor = call.from_user.full_name or call.from_user.username or "—"
    new_text = (
        f"{base_text}\n\n"
        f"<b>Статус:</b> {status_emoji(status)} {status}\n"
        f"<b>Кто:</b> {actor}"
    )

    if call.message.caption is not None:
        await call.message.edit_caption(
            caption=new_text,
            reply_markup=status_kb(req_id, status),
            parse_mode="HTML",
        )
    else:
        await call.message.edit_text(
            new_text,
            reply_markup=status_kb(req_id, status),
            parse_mode="HTML",
        )

    # Уведомление автору
    author = get_request_author(req_id)
    if author:
        author_id = author[0]
        if author_id != call.from_user.id:
            try:
                if status == "В обработке":
                    await bot.send_message(
                        author_id,
                        f"🔄 <b>Ваша заявка №{req_id} взята в работу</b>\n"
                        f"Ответственный: {actor}\n"
                        "Сообщим, как только будет решение.",
                        parse_mode="HTML",
                    )
                else:
                    await bot.send_message(
                        author_id,
                        f"✅ <b>Ваша заявка №{req_id} решена!</b>\n"
                        f"Закрыл: {actor}\n"
                        "Спасибо за обращение 🙌",
                        parse_mode="HTML",
                    )
            except Exception:
                pass  # пользователь мог не запускать бота в личке

    await call.answer(f"Статус: {status}")


# ================== FALLBACK ==================

@dp.message()
async def fallback(message: Message, state: FSMContext):
    if await state.get_state() is not None:
        return
    await message.answer(
        "Не понял команду. Откройте меню кнопкой ниже или напишите /help.",
        reply_markup=main_menu_for(message.from_user.id),
    )


# ================== RUN ==================

async def main():
    print("Bot starting…")
    me = await bot.get_me()
    print(f"Logged in as @{me.username} (id={me.id})")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

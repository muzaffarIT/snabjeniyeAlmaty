from aiogram.fsm.state import State, StatesGroup


class RequestFSM(StatesGroup):
    """
    FSM создания заявки по снабжению

    ПОРЯДОК ШАГОВ (НЕ МЕНЯТЬ):
    1. branch        — выбор филиала (один раз)
    2. category      — категория снабжения
    3. description   — описание проблемы
    4. media         — фото / видео (опционально)
    5. urgency       — срочность (СРОЧНО / ПЛАНОВО)
    6. confirm       — проверка перед отправкой
    """

    branch = State()
    category = State()
    description = State()
    media = State()
    urgency = State()
    confirm = State()

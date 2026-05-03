# snabjeniyeAlmaty

Telegram-бот учёта заявок снабжения для Алматы.

Филиалы: **Маркова**, **Саина**, **Саяхат**.

## Локальный запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # и заполни значения
python3 bot.py
```

## Переменные окружения

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `ADMIN_IDS` | Telegram user ID ответственных за снабжение, через запятую |
| `GROUP_ID` | ID супергруппы, куда падают заявки (бот должен быть в группе как админ) |
| `DATABASE_URL` | PostgreSQL connection string (на Railway подставится автоматически) |

## Деплой на Railway

1. Создать проект из этого репозитория.
2. Добавить плагин **PostgreSQL** — `DATABASE_URL` подставится сам.
3. В Variables проставить `BOT_TOKEN`, `ADMIN_IDS`, `GROUP_ID`.
4. Railway сам поднимет worker по `Procfile` (`python3 bot.py`).

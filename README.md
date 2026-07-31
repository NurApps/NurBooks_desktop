# NurBooks

Электронная исламская библиотека от NurApps. Десктоп-приложение на Flet (Python) с синхронизацией через Firebase/FastAPI-сервер.

## Структура проекта

```
├── src/                    # Десктоп-приложение (Flet)
│   ├── core/               # Логика: БД, загрузка, обновления, Firebase-клиент
│   └── ui/                 # Интерфейс: страницы и компоненты
├── server/                 # FastAPI-сервер (прокси к Firebase Firestore)
├── scripts/                # Админ-скрипты (загрузка книг, настройка Firestore)
├── tests/                  # Юнит-тесты (pytest)
└── assets/                 # Иконки и ресурсы
```

## Установка (разработка)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python src/ui/main.py
```

Запуск сервера локально:

```bash
cd server
pip install -r requirements.txt
uvicorn main:app --reload
```

Для работы сервера нужны Firebase-креды:
- файл `serviceAccountKey.json` в папке сервера, **или**
- переменная окружения `FIREBASE_SERVICE_ACCOUNT_JSON` с содержимым ключа.

## Тесты и линтинг

```bash
pip install -r requirements-dev.txt
pytest              # 60+ тестов
ruff check src server tests scripts add_book_gui.py installer-NurBooks.py
```

## Конфигурация сервера (переменные окружения)

| Переменная                | Назначение                                    | По умолчанию |
|---------------------------|-----------------------------------------------|--------------|
| `NURBOOKS_API_KEY`        | API-ключ (заголовок `X-API-Key`)              | пусто (нет проверки) |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | JSON-ключ сервисного аккаунта Firebase  | — |
| `CORS_ORIGINS`            | Разрешённые origin'ы через запятую            | пусто (CORS закрыт) |
| `RATE_LIMIT_MAX`          | Максимум запросов с IP за окно                | 120 |
| `RATE_LIMIT_WINDOW`       | Окно rate-limit, секунд                       | 60 |

## Версионирование

Версия приложения задаётся в `src/config.py` (`APP_VERSION`), версия сервера — в `server/main.py` (`APP_VERSION`). При релизе:
1. Поднимите версию в обоих местах.
2. Создайте git-тег вида `v1.3.5` — GitHub Actions соберёт EXE, инсталлятор и создаст релиз.
3. Список изменений фиксируйте в [CHANGELOG.md](CHANGELOG.md).

## Безопасность

- `serviceAccountKey.json` и `serviceAccount.json` не должны попадать в git (см. `.gitignore`).
- API-ключ передавайте заголовком `X-API-Key`, а не в URL.
- Токены Firebase Auth передаются заголовком `Authorization: Bearer <token>`.
- Не коммитьте токены, пароли и приватные ключи.

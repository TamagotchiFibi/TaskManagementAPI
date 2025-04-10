# Task Management API

![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.0-blue.svg)
![Redis](https://img.shields.io/badge/Redis-7.0-red.svg)
![Tests](https://img.shields.io/badge/tests-39%20passed-brightgreen.svg)

Современный API для управления задачами с аутентификацией, уведомлениями и кэшированием.

## Возможности

- Аутентификация и авторизация пользователей
- Создание и управление задачами
- Тегирование задач
- Система уведомлений
- Кэширование данных с Redis
- Отправка email-уведомлений
- Защита от атак (XSS, CSRF, Rate Limiting)
- Полное покрытие тестами (39 тестов)

## Требования

- Python 3.12+
- Redis 7.0+
- SQLite (для разработки) или PostgreSQL (для продакшена)
- Почтовый сервер (для отправки уведомлений)

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/task-management-api.git
cd task-management-api
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Скопируйте `.env.example` в `.env` и настройте переменные окружения:
```bash
cp .env.example .env
```

5. Отредактируйте `.env` файл:
```env
DATABASE_URL=sqlite:///./app.db
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
CACHE_TTL=3600
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_TIME=15
RATE_LIMIT=100
```

## Разработка

1. Создайте и активируйте виртуальное окружение для разработки:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

2. Установите зависимости для разработки:
```bash
pip install -r requirements.txt
```

3. Настройте pre-commit хуки:
```bash
pre-commit install
```

4. Запустите миграции:
```bash
alembic upgrade head
```

5. Запустите Redis:
```bash
redis-server
```

6. Запустите приложение в режиме разработки:
```bash
uvicorn app.main:app --reload --port 8000
```

## Тестирование

1. Создайте тестовую базу данных:
```bash
cp .env.example .env.test
```

2. Запустите тесты:
```bash
pytest -v
```

3. Запустите тесты с отчетом о покрытии:
```bash
pytest --cov=app --cov-report=html
```

4. Проверьте типы с помощью mypy:
```bash
mypy app
```

## API Документация

После запуска приложения доступны:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Развертывание

1. Настройте production окружение:
```bash
cp .env.example .env.prod
```

2. Обновите `.env.prod` с production настройками:
- Используйте PostgreSQL вместо SQLite
- Настройте SMTP сервер
- Установите надежный SECRET_KEY
- Настройте CORS и другие параметры безопасности

3. Запустите с помощью Docker:
```bash
docker-compose up -d
```

## Безопасность

- Защита от XSS атак
- CSRF токены для защиты форм
- Rate limiting для предотвращения DDoS
- Блокировка после 5 неудачных попыток входа
- Безопасное хранение паролей (bcrypt)
- JWT токены с ограниченным временем жизни
- Защита от SQL инъекций (SQLAlchemy)
- Secure headers (HSTS, CSP, X-Frame-Options)

## Структура проекта

```
task-management-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       └── router.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   └── database.py
│   ├── models/
│   ├── schemas/
│   └── utils/
│       ├── cache.py
│       ├── email.py
│       └── logger.py
├── tests/
├── alembic/
├── docker/
└── docs/
```

## Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой фичи (`git checkout -b feature/amazing-feature`)
3. Внесите изменения
4. Убедитесь, что все тесты проходят
5. Создайте pull request

## Лицензия

MIT License - смотрите файл [LICENSE](LICENSE)

## Авторы

shakhaaaeva@gmail.com

## Поддержка

Если у вас возникли проблемы:
1. Проверьте [Issues](https://github.com/yourusername/task-management-api/issues)
2. Создайте новый issue с подробным описанием проблемы
3. Свяжитесь с автором по email

Проект доступен на [GitHub](https://github.com/TamagotchiFibi/task-management-api) 
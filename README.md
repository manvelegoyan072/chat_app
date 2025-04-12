# Messenger API

Мессенджер в реальном времени, построенный на FastAPI, SQLAlchemy, Redis и с поддержкой WebSocket. Поддерживает аутентификацию пользователей с JWT-токенами, роли (пользователь/админ), групповые и личные чаты, защиту от CSRF и обмен сообщениями в реальном времени.

## Возможности

- **Аутентификация**: Вход с использованием JWT-токенов (access/refresh), хранимых в HTTP-only cookies.
- **Авторизация**: Ролевой доступ (пользователь, администратор).
- **Чаты**: Личные и групповые чаты с обменом сообщениями в реальном времени.
- **Безопасность**: Защита от CSRF, чёрный список токенов в Redis.
- **База данных**: PostgreSQL с миграциями через Alembic.
- **Мониторинг**: Prometheus и Grafana для визуализации метрик (HTTP-запросы, Redis, PostgreSQL, система).
- **Логирование**: Структурированные логи с ротацией файлов.

## Требования

- Python 3.11+
- Docker и Docker Compose
- PostgreSQL
- Redis

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone <repository-url>
   cd messenger
Создайте и настройте .env:
bash

Collapse

Wrap

Copy
cp .env.example .env
Соберите и запустите сервисы:
bash

Collapse

Wrap

Copy
docker-compose up --build
Примените миграции базы данных:
bash

Collapse

Wrap

Copy
docker-compose exec app alembic upgrade head
Мониторинг
Приложение использует Prometheus и Grafana для мониторинга:

Prometheus: Доступ по адресу http://localhost:9090
Собирает метрики с FastAPI (/metrics), Redis, PostgreSQL и системы.
Grafana: Доступ по адресу http://localhost:3000 (логин/пароль: admin/admin)
Дашборды: FastAPI (ID 11378), Redis (ID 763), PostgreSQL (ID 455), Node (ID 1860).
Оповещения: Настроены на высокий уровень ошибок (>5%) и задержки (>1с).
Для добавления собственных метрик:

Расширьте app/main.py с помощью prometheus_client для создания счётчиков/датчиков.
Обновите дашборды Grafana с новыми PromQL-запросами.
Использование
API: Документация доступна по адресу http://localhost:8000/docs
WebSocket: Подключение к /chats/{chat_id}?token={jwt_token} для обмена сообщениями в реальном времени.
Тестирование
Запустите тесты:

bash

Collapse

Wrap

Copy
pytest
Переменные окружения
Смотрите .env.example для подробностей:

DATABASE_URL: Строка подключения к PostgreSQL.
REDIS_HOST, REDIS_PORT: Подключение к Redis.
SECRET_KEY, CSRF_SECRET: Ключи безопасности.
LOG_LEVEL, LOG_FILE: Настройки логирования.
REDIS_MAX_CONNECTIONS: Размер пула соединений Redis.
Структура проекта
app/: Основной код приложения.
controllers/: Эндпоинты API и WebSocket.
services/: Бизнес-логика (пользователи, чаты, сообщения, Redis).
models/: Модели SQLAlchemy.
schemas/: Схемы Pydantic.
middlewares/: Middleware для CSRF.
logging_config.py: Настройка логирования.
alembic/: Миграции базы данных.
tests/: Юнит- и интеграционные тесты.
prometheus.yml, prometheus-rules.yml: Конфигурация Prometheus.
docker-compose.yml: Сервисы Docker (приложение, БД, Redis, мониторинг).
Детали мониторинга
Метрики FastAPI: Количество запросов, длительность, уровень ошибок.
Метрики Redis: Частота команд, использование памяти, количество соединений.
Метрики PostgreSQL: Производительность запросов, активные соединения.
Метрики системы: Загрузка CPU, память, диск.
Оповещения срабатывают при >5% ошибок 5xx или задержке >1с (99-й перцентиль).
Участие
Сделайте форк репозитория.
Создайте ветку для новой функции (git checkout -b feature-name).
Зафиксируйте изменения (git commit -m 'Добавлена функция').
Отправьте ветку в репозиторий (git push origin feature-name).
Откройте Pull Request.
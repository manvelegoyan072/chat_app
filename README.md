
# Messenger API

Мессенджер в реальном времени, построенный на FastAPI, SQLAlchemy, Redis и с поддержкой WebSocket. Поддерживает аутентификацию пользователей с JWT-токенами, роли (пользователь/админ), групповые и личные чаты, защиту от CSRF и обмен сообщениями в реальном времени.

##  Возможности

- **Аутентификация**: JWT-токены (access/refresh) в HTTP-only cookies.
- **Авторизация**: Ролевой доступ (пользователь, администратор).
- **Чаты**: Личные и групповые чаты с WebSocket-поддержкой.
- **Безопасность**: CSRF-защита, чёрный список токенов в Redis.
- **База данных**: PostgreSQL с Alembic-механизмом миграций.
- **Мониторинг**: Prometheus и Grafana для метрик (HTTP, Redis, PostgreSQL, система).
- **Логирование**: Структурированное логирование с ротацией.

##  Требования

- Python 3.11+
- Docker и Docker Compose
- PostgreSQL
- Redis

##  Установка

1. Клонируйте репозиторий:
   ```bash
   git clone <repository-url>
   cd messenger
   ```

2. Создайте и настройте `.env`:
   ```bash
   cp .env.example .env
   ```

3. Соберите и запустите сервисы:
   ```bash
   docker-compose up --build
   ```

4. Примените миграции базы данных:
   ```bash
   docker-compose exec app alembic upgrade head
   ```

##  Мониторинг

Приложение использует Prometheus и Grafana для мониторинга.

- **Prometheus**: http://localhost:9090  
  Сбор метрик с FastAPI (`/metrics`), Redis, PostgreSQL и системы.

- **Grafana**: http://localhost:3000  
  Логин: `admin` / Пароль: `admin`

  Дашборды:
  - FastAPI: ID `11378`
  - Redis: ID `763`
  - PostgreSQL: ID `455`
  - Node/System: ID `1860`

- **Оповещения**:
  - Ошибки 5xx > 5%
  - Задержка > 1s (99-й перцентиль)

### Добавление собственных метрик:

- Используйте `prometheus_client` в `app/main.py`.
- Обновите Grafana-дэшборды PromQL-запросами.

##  Использование

- **API-документация**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **WebSocket**:  
  Подключение к чату:  
  ```
  /chats/{chat_id}?token={jwt_token}
  ```

##  Тестирование

Запуск тестов:
```bash
pytest
```

##  Переменные окружения

Подробнее см. `.env.example`:

- `DATABASE_URL`: Строка подключения к PostgreSQL.
- `REDIS_HOST`, `REDIS_PORT`: Подключение к Redis.
- `SECRET_KEY`, `CSRF_SECRET`: Ключи безопасности.
- `LOG_LEVEL`, `LOG_FILE`: Настройки логирования.
- `REDIS_MAX_CONNECTIONS`: Размер пула Redis-соединений.

##  Структура проекта

```
app/
├── controllers/       # Эндпоинты API и WebSocket
├── services/          # Бизнес-логика (пользователи, чаты, Redis)
├── models/            # SQLAlchemy-модели
├── schemas/           # Pydantic-схемы
├── middlewares/       # CSRF Middleware
├── logging_config.py  # Логирование
alembic/               # Миграции базы данных
tests/                 # Тесты
prometheus.yml         # Конфигурация Prometheus
prometheus-rules.yml   # Алёрты
docker-compose.yml     # Docker-сервисы
```

##  Детали мониторинга

- **FastAPI**: Кол-во запросов, ошибки, задержка.
- **Redis**: Команды, память, соединения.
- **PostgreSQL**: Запросы, соединения.
- **Система**: CPU, RAM, диск.

Оповещения:
- Ошибки 5xx > 5%
- Задержка > 1s (99-й перцентиль)


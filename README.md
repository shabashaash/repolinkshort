## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DATABASE_URL` | Подключение к PostgreSQL | `postgresql://postgres:postgres@db:5432/shortlink` |
| `REDIS_URL` | Подключение к Redis | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Брокер для Celery | `redis://redis:6379/1` |
| `SECRET_KEY` | Ключ для подписи JWT | — |
| `DEFAULT_LINK_EXPIRE_DAYS` | Срок жизни ссылки по умолчанию | `30` |
| `UNUSED_LINK_DELETE_DAYS` | Удаление неиспользуемых ссылок через N дней | `90` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни токена в минутах | `30` |

## Запуск

```bash
# Клонирование 
git clone <repo-url>
cd <project-folder>
# Копирование переменных окружения
cp .env.example .env
# Сборка и запуск
docker-compose up --build -d
```
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

## База данных

### `users`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | INTEGER | Первичный ключ |
| `email` | VARCHAR(255) | Уникальный email |
| `password_hash` | VARCHAR(255) | Хэш пароля (bcrypt) |
| `created_at` | TIMESTAMP | Дата создания |
| `is_active` | BOOLEAN | Активен ли пользователь |

### `links`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | INTEGER | Первичный ключ |
| `user_id` | INTEGER | Внешний ключ на users |
| `short_code` | VARCHAR(10) | Уникальный код ссылки |
| `original_url` | TEXT | Оригинальный URL |
| `custom_alias` | VARCHAR(50) | Кастомный alias (опционально) |
| `project` | VARCHAR(100) | Проект/группа |
| `expires_at` | TIMESTAMP | Срок действия (опционально) |
| `click_count` | INTEGER | Счётчик кликов |
| `last_clicked_at` | TIMESTAMP | Последний клик |
| `created_at` | TIMESTAMP | Дата создания |

## API 

### Публичные

| Метод | Путь | Описание |
|-------|-----|----------|
| `GET` | `/{short_code}` | Перенаправление по короткой ссылке |
| `GET` | `/api/links/{short_code}` | Информация о ссылке |

### Аутентификация

| Метод | Путь | Описание |
|-------|-----|----------|
| `POST` | `/api/auth/register` | Регистрация нового пользователя |
| `POST` | `/api/auth/login` | Вход, получение токена |

### Ссылки (требуют токен)

| Метод | Путь | Описание |
|-------|-----|----------|
| `POST` | `/api/links` | Создать короткую ссылку |
| `GET` | `/api/links` | Список ссылок пользователя |
| `GET` | `/api/links/{id}` | Детали ссылки |
| `PATCH` | `/api/links/{id}` | Обновить ссылку |
| `DELETE` | `/api/links/{id}` | Удалить ссылку |
| `GET` | `/api/links/{id}/stats` | Статистика по ссылке |

## Примеры запросов

### Регистрация

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@mail.com","password":"pass123"}'
```

**Ответ:**

```json
{
  "id": 1,
  "email": "user@mail.com",
  "created_at": "..."
}
```

---

### Вход

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@mail.com","password":"pass123"}'
```

**Ответ:**

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

---

### Создание ссылки

```bash
curl -X POST http://localhost:8000/api/links \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://example.com",
    "project": "project"
  }'
```

**Ответ:**

```json
{
  "id": 1,
  "short_code": "abc123",
  "short_url": "http://localhost:8000/abc123",
  "original_url": "https://example.com",
  "project": "project",
  "click_count": 0,
  "expires_at": "...",
  "created_at": "..."
}
```

---

### Создание ссылки с кастомным alias

```bash
curl -X POST http://localhost:8000/api/links \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://example.com",
    "custom_alias": "custom-link"
  }'
```

**Ответ:**

```json
{
  "id": 2,
  "short_code": "custom-link",
  "short_url": "http://localhost:8000/custom-link",
  "original_url": "https://example.com",
  "click_count": 0,
  "created_at": "..."
}
```

---

### Переход по короткой ссылке

```bash
curl -v http://localhost:8000/abc123
```

---

### Получение статистики ссылки

```bash
curl -X GET http://localhost:8000/api/links/1/stats \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Ответ:**

```json
{
  "id": 1,
  "short_code": "abc123",
  "click_count": 1,
  "last_clicked_at": "...",
  "created_at": "..."
}
```

---

### Список ссылок пользователя

```bash
curl -X GET "http://localhost:8000/api/links?project=marketing" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Ответ:**

```json
{
  "items": [
    {
      "id": 1,
      "short_code": "abc123",
      "short_url": "http://localhost:8000/abc123",
      "original_url": "https://example.com",
      "project": "project",
      "click_count": 1,
      "created_at": "..."
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10
}
```

## Фоновые задачи

Celery для очистки ссылок:

- **cleanup_expired_links** — каждый час удаляет просроченные ссылки
- **cleanup_unused_links** — каждый день удаляет ссылки, которые не использовались более N дней (настраивается через `UNUSED_LINK_DELETE_DAYS`)

# Nazar VK Bot

VK-бот для управления заявками на пробный доступ и подписки сервиса Nazar VPN.

## Возможности

- Обработка сообщений сообщества ВКонтакте.
- Главное меню и навигация по разделам.
- Оформление заявки на пробный доступ.
- Просмотр тарифов подписки.
- Создание демонстрационных заказов.
- Выбор демонстрационного способа оплаты.
- Интеграция с внешним API Nazar VPN.
- Хранение данных в PostgreSQL.

## Важно

Этот проект — бот для взаимодействия с пользователями через ВКонтакте. Сам по себе он не является VPN-сервером.

Для работы функций пробного доступа и подписок требуется отдельно развёрнутый совместимый API Nazar VPN.

Текущий сценарий оформления заказа и выбора способа оплаты демонстрационный. Он не принимает реальные платежи и не подтверждает фактическую оплату.

## Требования

- Linux-сервер.
- Docker.
- Docker Compose Plugin.
- Сообщество ВКонтакте с включённым Callback API.
- Совместимый API Nazar VPN.

## Установка

### 1. Получение проекта

```bash
git clone https://github.com/USERNAME/nazar-vk-bot.git
cd nazar-vk-bot
```

Замените `USERNAME` на имя своего GitHub-аккаунта.

### 2. Настройка переменных окружения

Создайте файл `.env` на основе шаблона:

```bash
cp .env.example .env
nano .env
```

Заполните параметры своими значениями.

### 3. Настройка переменных

| Переменная | Назначение |
|---|---|
| `POSTGRES_DB` | Имя базы PostgreSQL |
| `POSTGRES_USER` | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL |
| `DATABASE_URL` | Строка подключения к базе |
| `VK_GROUP_ID` | ID сообщества ВКонтакте |
| `VK_GROUP_TOKEN` | Токен сообщества |
| `VK_CALLBACK_SECRET` | Секрет Callback API |
| `VK_CONFIRMATION_CODE` | Строка подтверждения Callback API |
| `VK_API_VERSION` | Версия VK API |
| `VK_API_URL` | Адрес API Nazar VPN |
| `VK_INTERNAL_API_KEY` | Ключ доступа к внутреннему API |

**Не публикуйте файл `.env` и не передавайте никому свои токены и ключи.**

### 4. Запуск

```bash
docker compose --env-file .env -f compose.github.yaml up -d --build
```

Проверить состояние контейнеров:

```bash
docker compose --env-file .env -f compose.github.yaml ps
```

Посмотреть журнал:

```bash
docker compose --env-file .env -f compose.github.yaml logs -f bot
```

### 5. Проверка работы

Главная страница:

```text
http://SERVER-IP:8000/
```

Проверка состояния:

```text
http://SERVER-IP:8000/health
```

Для Callback API ВКонтакте укажите адрес:

```text
https://YOUR-DOMAIN/vk/callback
```

Домен должен вести на сервер, а HTTPS должен быть настроен отдельно.

## Интеграция с Nazar VPN API

Бот использует следующие внутренние API-методы:

- `POST /internal/vk/trial` — запрос пробного доступа.
- `POST /internal/vk/subscription` — запрос подписки.

Для запросов используется заголовок `X-Internal-API-Key`.

Формат передаваемых данных:

```json
{
  "vk_id": 123456789
}
```

Адрес API и ключ доступа задаются через `.env`.

## Обновление

Получить изменения из GitHub:

```bash
git pull
```

Пересобрать и перезапустить:

```bash
docker compose --env-file .env -f compose.github.yaml up -d --build
```

## Остановка

```bash
docker compose --env-file .env -f compose.github.yaml down
```

## Безопасность

- Не добавляйте `.env` в Git.
- Не публикуйте токены и API-ключи.
- Используйте уникальные пароли.
- Не открывайте PostgreSQL напрямую в интернет.
- Настройте HTTPS для Callback API.

## Лицензия

Лицензия проекта пока не определена.# Nazar VK Bot

VK-бот для управления заявками на пробный доступ и подписки сервиса Nazar VPN.

## Возможности

- Обработка сообщений сообщества ВКонтакте.
- Главное меню и навигация по разделам.
- Оформление заявки на пробный доступ.
- Просмотр тарифов подписки.
- Создание демонстрационных заказов.
- Выбор демонстрационного способа оплаты.
- Интеграция с внешним API Nazar VPN.
- Хранение данных в PostgreSQL.

## Важно

Этот проект — бот для взаимодействия с пользователями через ВКонтакте. Сам по себе он не является VPN-сервером.

Для работы функций пробного доступа и подписок требуется отдельно развёрнутый совместимый API Nazar VPN.

Текущий сценарий оформления заказа и выбора способа оплаты демонстрационный. Он не принимает реальные платежи и не подтверждает фактическую оплату.

## Требования

- Linux-сервер.
- Docker.
- Docker Compose Plugin.
- Сообщество ВКонтакте с включённым Callback API.
- Совместимый API Nazar VPN.

## Установка

### 1. Получение проекта

```bash
git clone https://github.com/USERNAME/nazar-vk-bot.git
cd nazar-vk-bot
```

Замените `USERNAME` на имя своего GitHub-аккаунта.

### 2. Настройка переменных окружения

Создайте файл `.env` на основе шаблона:

```bash
cp .env.example .env
nano .env
```

Заполните параметры своими значениями.

### 3. Настройка переменных

| Переменная | Назначение |
|---|---|
| `POSTGRES_DB` | Имя базы PostgreSQL |
| `POSTGRES_USER` | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL |
| `DATABASE_URL` | Строка подключения к базе |
| `VK_GROUP_ID` | ID сообщества ВКонтакте |
| `VK_GROUP_TOKEN` | Токен сообщества |
| `VK_CALLBACK_SECRET` | Секрет Callback API |
| `VK_CONFIRMATION_CODE` | Строка подтверждения Callback API |
| `VK_API_VERSION` | Версия VK API |
| `VK_API_URL` | Адрес API Nazar VPN |
| `VK_INTERNAL_API_KEY` | Ключ доступа к внутреннему API |

**Не публикуйте файл `.env` и не передавайте никому свои токены и ключи.**

### 4. Запуск

```bash
docker compose --env-file .env -f compose.github.yaml up -d --build
```

Проверить состояние контейнеров:

```bash
docker compose --env-file .env -f compose.github.yaml ps
```

Посмотреть журнал:

```bash
docker compose --env-file .env -f compose.github.yaml logs -f bot
```

### 5. Проверка работы

Главная страница:

```text
http://SERVER-IP:8000/
```

Проверка состояния:

```text
http://SERVER-IP:8000/health
```

Для Callback API ВКонтакте укажите адрес:

```text
https://YOUR-DOMAIN/vk/callback
```

Домен должен вести на сервер, а HTTPS должен быть настроен отдельно.

## Интеграция с Nazar VPN API

Бот использует следующие внутренние API-методы:

- `POST /internal/vk/trial` — запрос пробного доступа.
- `POST /internal/vk/subscription` — запрос подписки.

Для запросов используется заголовок `X-Internal-API-Key`.

Формат передаваемых данных:

```json
{
  "vk_id": 123456789
}
```

Адрес API и ключ доступа задаются через `.env`.

## Обновление

Получить изменения из GitHub:

```bash
git pull
```

Пересобрать и перезапустить:

```bash
docker compose --env-file .env -f compose.github.yaml up -d --build
```

## Остановка

```bash
docker compose --env-file .env -f compose.github.yaml down
```

## Безопасность

- Не добавляйте `.env` в Git.
- Не публикуйте токены и API-ключи.
- Используйте уникальные пароли.
- Не открывайте PostgreSQL напрямую в интернет.
- Настройте HTTPS для Callback API.

## Лицензия

Лицензия проекта пока не определена.

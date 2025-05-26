# Foodgram - сайт для публикации рецептов

Платформа для публикации рецептов, составления списка покупок и подписки на авторов.

## Что умеет Foodgram

- Публикация рецептов с фото, ингредиентами и тегами
- Добавление рецептов в избранное
- Подписки на авторов
- Составление списка покупок на основе выбранных рецептов
- Выгрузка списка покупок в TXT-файл
- Короткие ссылки на рецепты для удобного шеринга

## Технологии

- Python 3.11
- Django REST Framework
- PostgreSQL
- Docker
- React (фронтенд)
- GitHub Actions CI/CD

## Как запустить проект

### Подготовка

1. Клонировать репозиторий
2. Перейти в директорию с проектом

### Добавление перменных окружения

В директории `/infra` создайте файл `.env` (см. пример в файле `.env.example`)

### Запуск с использованием Docker

```bash
cd infra

docker-compose up -d

docker-compose exec backend python manage.py migrate

docker-compose exec backend python manage.py collectstatic
```

### Создание суперпользователя

```bash
docker-compose exec backend python manage.py createsuperuser
```

### Загрузка тестовых данных

```bash
docker-compose exec backend python manage.py load_ingredients
```

### Доступ к проекту

После запуска сервисы доступны по адресам:
- Фронтенд: http://localhost/
- API: http://localhost/api/
- Админ-панель: http://localhost/admin/

## Документация API

Документация доступна после запуска по адресу:
```
http://localhost/api/docs/
```

## CI/CD с GitHub Actions

Проект настроен на автоматическую сборку и публикацию образов Docker:

1. Запускаются тесты Django и React
2. Создаются и отправляются образы Docker на DockerHub:
   - foodgram_backend
   - foodgram_frontend
   - foodgram_gateway
3. Отправляется уведомление в Telegram о успешной публикации образов

### Требуемые секреты GitHub

Для работы CI/CD в репозитории необходимо добавить следующие секреты:
- `DOCKER_USERNAME` - имя пользователя DockerHub
- `DOCKER_PASSWORD` - пароль от DockerHub
- `TELEGRAM_TO` - ID чата Telegram для уведомлений о сборке отзыва
- `TELEGRAM_TOKEN` - токен бота Telegram

## Остановка проекта

```bash
docker-compose down
```

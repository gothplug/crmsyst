# Мини CRM (Django + Bootstrap)

Мини-CRM по макету из Figma с полноценным бэкендом на Django и интерфейсом на Bootstrap 5.

## Структура

- `manage.py`, `crm_site/` — Django‑проект.
- `leads/` — приложение с моделями лидов, статусами, историей, CSV‑импортом, канбан‑доской и отчётом «Воронка».
- `templates/` — базовый шаблон и шаблоны приложения.
- `tz.txt` — исходное техническое задание.

## Технологии

- Django (SQLite по умолчанию).
- Bootstrap 5 через CDN.

## Установка и запуск

1. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

2. Выполните миграции и создайте суперпользователя (по желанию):

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

3. Запустите сервер разработки:

   ```bash
   python manage.py runserver
   ```

4. Откройте `http://127.0.0.1:8000/` в браузере.



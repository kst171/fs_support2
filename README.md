# HelpDesk Pro

Веб-приложение для регистрации обращений в центр технической поддержки.  
Стек: **Python 3.10+** · **Flask** · **PostgreSQL** · **SQLAlchemy**

---

## Быстрый старт

### 1. Клонируйте / скопируйте проект

```bash
cd support_app
```

### 2. Создайте виртуальное окружение

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 3. Установите зависимости

```bash
pip install -r requirements.txt
```

### 4. Настройте базу данных PostgreSQL

```sql
-- Выполните в psql или pgAdmin
CREATE DATABASE support_db;
CREATE USER support_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE support_db TO support_user;
```

### 5. Создайте файл `.env`

Скопируйте `.env.example` и заполните:

```bash
cp .env.example .env
```

```ini
DATABASE_URL=postgresql://support_user:your_password@localhost:5432/support_db
SECRET_KEY=замените-на-случайную-строку
FLASK_ENV=development
FLASK_DEBUG=1
```

### 6. Инициализируйте базу данных

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 7. (Опционально) Загрузите тестовые данные

```bash
flask seed-db
```

### 8. Запустите приложение

```bash
python app.py
```

Откройте браузер: **http://localhost:5000**

---

## Структура проекта

```
support_app/
├── app.py               # Маршруты и логика Flask
├── models.py            # Модели SQLAlchemy (Ticket, Comment)
├── requirements.txt     # Зависимости
├── .env.example         # Пример конфигурации
├── templates/
│   ├── base.html        # Базовый шаблон с сайдбаром
│   ├── index.html       # Дашборд со статистикой
│   ├── tickets.html     # Список обращений + фильтры
│   ├── new_ticket.html  # Форма создания обращения
│   └── ticket_detail.html  # Детали + комментарии + управление
└── static/
    ├── css/style.css    # Стили (dark theme)
    └── js/main.js       # Вспомогательные скрипты
```

---

## Функциональность

| Функция | Описание |
|---|---|
| 📋 Дашборд | Статистика по статусам и приоритетам |
| ➕ Создание обращений | Форма с валидацией, авто-номер TKT-YYYY-XXXXX |
| 🔍 Поиск и фильтры | По статусу, приоритету, категории, тексту |
| ✏️ Редактирование | Смена статуса, приоритета, исполнителя |
| 💬 Комментарии | Публичные и внутренние заметки |
| 🗑️ Удаление | С подтверждением |
| 📄 Пагинация | 15 записей на странице |

### Приоритеты
- 🟢 Низкий · 🟡 Средний · 🟠 Высокий · 🔴 Критический

### Статусы
- Открыто → В работе → Ожидание → Закрыто

### Категории
Оборудование · ПО · Сеть · Доступы · Почта · Прочее

---

## Деплой в продакшн

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Для Nginx — проксируйте на порт 8000.  
Установите `FLASK_ENV=production` и `FLASK_DEBUG=0` в `.env`.

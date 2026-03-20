import os
import random
import string
import pytz
import uuid
import logging
from datetime import datetime, date
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_migrate import Migrate
from dotenv import load_dotenv
from models import db, Ticket, Comment, Attachment, now_local

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/support_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

logging.basicConfig(level=logging.DEBUG)

UPLOAD_FOLDER = '/app/uploads'
ALLOWED_EXTENSIONS = {
    # изображения
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp',
    # текстовые
    'txt', 'log', 'csv', 'json', 'xml', 'md',
    # документы
    'pdf', 'doc', 'docx', 'xls', 'xlsx',
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file(file):
    original = secure_filename(file.filename)
    ext      = original.rsplit('.', 1)[1].lower() if '.' in original else ''
    saved    = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    path     = os.path.join(app.config['UPLOAD_FOLDER'], saved)
    file.save(path)
    size     = os.path.getsize(path)
    app.logger.debug(f"Файл сохранён: {path}, размер: {size}")
    return original, saved, file.mimetype, size

db.init_app(app)
migrate = Migrate(app, db)


def generate_ticket_number():
    """Генерация номера обращения по порядку вида FS-2026-00001."""
    year = datetime.now().year
    last = Ticket.query.filter(
        Ticket.ticket_number.like(f'FS-{year}-%')
    ).order_by(Ticket.ticket_number.desc()).first()

    if last:
        try:
            num = int(last.ticket_number.split('-')[-1]) + 1
        except ValueError:
            num = 1
    else:
        num = 1

    return f"FS-{year}-{num:05d}"


# ─── Главная / дашборд ────────────────────────────────────────────────────────

@app.route('/')
def index():
    total       = Ticket.query.count()
    open_count  = Ticket.query.filter_by(status='open').count()
    in_progress = Ticket.query.filter_by(status='in_progress').count()
    closed      = Ticket.query.filter_by(status='closed').count()
    waiting     = Ticket.query.filter_by(status='waiting').count()
    critical    = Ticket.query.filter_by(priority='critical').count()
    recent      = Ticket.query.order_by(Ticket.created_at.desc()).limit(5).all()

    # ── Активный фильтр с дашборда ────────────────────────
    active_filter = request.args.get('filter', None)
    filter_tickets = None

    if active_filter == 'open':
        filter_tickets = Ticket.query.filter_by(status='open').order_by(Ticket.created_at.desc()).all()
    elif active_filter == 'in_progress':
        filter_tickets = Ticket.query.filter_by(status='in_progress').order_by(Ticket.created_at.desc()).all()
    elif active_filter == 'waiting':
        filter_tickets = Ticket.query.filter_by(status='waiting').order_by(Ticket.created_at.desc()).all()
    elif active_filter == 'closed':
        filter_tickets = Ticket.query.filter_by(status='closed').order_by(Ticket.created_at.desc()).all()
    elif active_filter == 'critical':
        filter_tickets = Ticket.query.filter_by(priority='critical').order_by(Ticket.created_at.desc()).all()
    elif active_filter == 'total':
        filter_tickets = Ticket.query.order_by(Ticket.created_at.desc()).all()

    stats = {
        'total': total,
        'open': open_count,
        'in_progress': in_progress,
        'closed': closed,
        'waiting': waiting,
        'critical': critical,
    }
    return render_template('index.html', stats=stats, recent=recent,
                           active_filter=active_filter, filter_tickets=filter_tickets)


# ─── Список обращений ─────────────────────────────────────────────────────────

@app.route('/tickets')
def tickets():
    status_filter   = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    category_filter = request.args.get('category', 'all')
    customer_filter = request.args.get('customer', '').strip()  # ← новый
    search_query    = request.args.get('q', '').strip()
    date_from       = request.args.get('date_from', '').strip()
    date_to         = request.args.get('date_to', '').strip()
    page            = request.args.get('page', 1, type=int)

    query = Ticket.query

    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)
    if category_filter != 'all':
        query = query.filter_by(category=category_filter)
    if customer_filter:                                          # ← новый
        query = query.filter(
            db.or_(
                Ticket.user_name.ilike(f'%{customer_filter}%'),
                Ticket.department.ilike(f'%{customer_filter}%'),
            )
        )
    if search_query:
        like = f'%{search_query}%'
        query = query.filter(
            db.or_(
                Ticket.title.ilike(like),
                Ticket.ticket_number.ilike(like),
                Ticket.user_name.ilike(like),
                Ticket.user_email.ilike(like),
            )
        )
    if date_from:
        try:
            df = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Ticket.created_at >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d')
            dt = dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Ticket.created_at <= dt)
        except ValueError:
            pass

    tickets_paginated = query.order_by(Ticket.created_at.desc()).paginate(page=page, per_page=15)

    # Список уникальных заказчиков для выпадающего списка
    customers = db.session.query(Ticket.user_name).distinct().order_by(Ticket.user_name).all()
    customers = [c[0] for c in customers if c[0]]

    return render_template(
        'tickets.html',
        tickets=tickets_paginated,
        status_filter=status_filter,
        priority_filter=priority_filter,
        category_filter=category_filter,
        customer_filter=customer_filter,
        search_query=search_query,
        date_from=date_from,
        date_to=date_to,
        customers=customers,
    )


# ─── Создание обращения ───────────────────────────────────────────────────────

@app.route('/tickets/new', methods=['GET', 'POST'])
def new_ticket():
    if request.method == 'POST':
        ticket_number = generate_ticket_number()
            
        ticket = Ticket(
            ticket_number = ticket_number,
            title         = request.form['title'],
            description   = request.form['description'],
            user_name     = request.form['user_name'],
            user_email    = request.form['user_email'],
            user_phone    = request.form.get('user_phone', '').strip() or None,
            department    = request.form.get('department', '').strip() or None,
            category      = request.form['category'],
            priority      = request.form['priority'],
            assigned_to   = request.form.get('assigned_to', '').strip() or None,
        )
        db.session.add(ticket)
        db.session.flush()  # получаем ticket.id до commit

        # ── Сохранение вложений ───────────────────────────
        files = request.files.getlist('attachments')
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                original, saved, mime, size = save_file(file)
                attachment = Attachment(
                    ticket_id  = ticket.id,
                    filename   = original,
                    saved_name = saved,
                    mimetype   = mime,
                    size       = size,
                )
                db.session.add(attachment)

        db.session.commit()
        flash(f'Обращение {ticket_number} успешно зарегистрировано!', 'success')
        return redirect(url_for('ticket_detail', id=ticket.id))

    return render_template('new_ticket.html')


# ─── Детали обращения ─────────────────────────────────────────────────────────

@app.route('/tickets/<int:id>', methods=['GET', 'POST'])
def ticket_detail(id):
    ticket = Ticket.query.get_or_404(id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_status':
            new_status = request.form['status']
            ticket.status = new_status
            ticket.updated_at = datetime.utcnow()
            if new_status == 'closed' and not ticket.closed_at:
                ticket.closed_at = datetime.utcnow()
                ticket.resolution = request.form.get('resolution', ticket.resolution)
            db.session.commit()
            flash('Статус обращения обновлён.', 'success')

        elif action == 'add_comment':
            comment = Comment(
                ticket_id   = ticket.id,
                author      = request.form['author'],
                text        = request.form['text'],
                is_internal = 'is_internal' in request.form,
            )
            db.session.add(comment)
            db.session.flush()

    # ── Вложения и сохранение вложений к комментарию ────────────────────────────
            files = request.files.getlist('attachments')
            print(f"DEBUG: получено файлов = {len(files)}", flush=True)
            for file in files:
                print(f"DEBUG: файл = '{file.filename}', тип = '{file.mimetype}'", flush=True)
                if file and file.filename and allowed_file(file.filename):
                    original, saved, mime, size = save_file(file)
                    print(f"DEBUG: сохранён как = '{saved}', размер = {size}", flush=True)
                    attachment = Attachment(
                        ticket_id  = ticket.id,
                        filename   = original,
                        saved_name = saved,
                        mimetype   = mime,
                        size       = size,
                    )
                    db.session.add(attachment)
                else:
                    print(f"DEBUG: файл отклонён — пустое имя или недопустимый тип", flush=True)

            ticket.updated_at = now_local()
            db.session.commit()
            flash('Комментарий добавлен.', 'success')

        elif action == 'update_ticket':
            ticket.title       = request.form['title']
            ticket.priority    = request.form['priority']
            ticket.assigned_to = request.form.get('assigned_to', '').strip() or None
            ticket.category    = request.form['category']
            ticket.updated_at  = datetime.utcnow()
            db.session.commit()
            flash('Обращение обновлено.', 'success')

        return redirect(url_for('ticket_detail', id=ticket.id))

    comments = Comment.query.filter_by(ticket_id=ticket.id).order_by(Comment.created_at.asc()).all()
    return render_template('ticket_detail.html', ticket=ticket, comments=comments)


# ─── Удаление обращения ───────────────────────────────────────────────────────

@app.route('/tickets/<int:id>/delete', methods=['POST'])
def delete_ticket(id):
    ticket = Ticket.query.get_or_404(id)
    db.session.delete(ticket)
    db.session.commit()
    flash(f'Обращение {ticket.ticket_number} удалено.', 'warning')
    return redirect(url_for('tickets'))


# ─── API для статистики (AJAX) ────────────────────────────────────────────────

@app.route('/api/stats')
def api_stats():
    stats = {
        'open':        Ticket.query.filter_by(status='open').count(),
        'in_progress': Ticket.query.filter_by(status='in_progress').count(),
        'waiting':     Ticket.query.filter_by(status='waiting').count(),
        'closed':      Ticket.query.filter_by(status='closed').count(),
    }
    return jsonify(stats)


# ─── Инициализация БД ─────────────────────────────────────────────────────────

@app.cli.command('init-db')
def init_db():
    """Создать таблицы в базе данных."""
    db.create_all()
    print('База данных инициализирована.')


@app.cli.command('seed-db')
def seed_db():
    """Заполнить БД тестовыми данными."""
    samples = [
        ('Не работает принтер в бухгалтерии', 'Принтер HP LaserJet не печатает, горит красный индикатор.', 'Анна Петрова', 'anna@company.ru', 'hardware', 'high', 'Бухгалтерия'),
        ('Забыл пароль от корпоративной почты', 'Нужно сбросить пароль от Outlook.', 'Иван Смирнов', 'ivan@company.ru', 'access', 'medium', 'Продажи'),
        ('Медленно работает интернет', 'Скорость упала до 1 Мбит/с, не могу работать с 1С.', 'Ольга Козлова', 'olga@company.ru', 'network', 'high', 'Склад'),
        ('Установить Microsoft Office', 'На новом компьютере нет Office, нужна установка.', 'Пётр Новиков', 'petr@company.ru', 'software', 'low', 'HR'),
        ('Синий экран на ноутбуке', 'Ноутбук падает в BSOD при запуске тяжёлых приложений.', 'Мария Иванова', 'maria@company.ru', 'hardware', 'critical', 'ИТ-отдел'),
    ]
    for title, desc, name, email, cat, pri, dept in samples:
        number = generate_ticket_number()
        t = Ticket(ticket_number=number, title=title, description=desc,
                   user_name=name, user_email=email, category=cat,
                   priority=pri, department=dept)
        db.session.add(t)
    db.session.commit()
    print('Тестовые данные добавлены.')


@app.template_filter('localtime')
def localtime_filter(dt):
    """Фильтр для шаблонов: {{ ticket.created_at | localtime }}"""
    if not dt:
        return ''
    tz = pytz.timezone(os.getenv('TIMEZONE', 'Europe/Moscow'))
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    local_dt = dt.astimezone(tz)
    return local_dt.strftime('%d.%m.%Y %H:%M')


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Отдать файл браузеру."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/uploads/<filename>/view')
def view_file(filename):
    """Отображение текстового файла в браузере."""
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(path):
        return 'Файл не найден', 404

    TEXT_EXTENSIONS = {'txt', 'log', 'csv', 'json', 'xml', 'md'}
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    if ext not in TEXT_EXTENSIONS:
        return 'Просмотр недоступен для этого типа файла', 400

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(path, 'r', encoding='cp1251') as f:
            content = f.read()

    # Получаем оригинальное имя из БД
    att = Attachment.query.filter_by(saved_name=filename).first()
    original_name = att.filename if att else filename

    return render_template('view_file.html', content=content,
                           filename=original_name, ext=ext)


@app.route('/attachments/<int:att_id>/delete', methods=['POST'])
def delete_attachment(att_id):
    att  = Attachment.query.get_or_404(att_id)
    tid  = att.ticket_id
    path = os.path.join(app.config['UPLOAD_FOLDER'], att.saved_name)
    if os.path.exists(path):
        os.remove(path)
    db.session.delete(att)
    db.session.commit()
    flash('Вложение удалено.', 'warning')
    return redirect(url_for('ticket_detail', id=tid))


@app.route('/api/logs')
def api_logs():
    """Последние 50 строк логов веб-сервера из памяти."""
    return jsonify(app_logs[-50:])


# Хранилище логов в памяти
app_logs = []

# Хранилище логов в памяти
app_logs = []

class MemoryLogHandler(logging.Handler):
    def emit(self, record):
        try:
            app_logs.append({
                'time':    datetime.now().strftime('%H:%M:%S'),
                'level':   record.levelname,
                'message': record.getMessage(),
            })
            if len(app_logs) > 200:
                app_logs.pop(0)
        except Exception:
            pass

memory_handler = MemoryLogHandler()
logging.getLogger('werkzeug').addHandler(memory_handler)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
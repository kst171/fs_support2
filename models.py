from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
import os

db = SQLAlchemy()

def now_local():
    """Возвращает текущее время в локальном часовом поясе."""
    tz = pytz.timezone(os.getenv('TIMEZONE', 'Europe/Moscow'))
    return datetime.now(tz).replace(tzinfo=None)  # сохраняем без tzinfo в БД


class Ticket(db.Model):
    __tablename__ = 'tickets'

    id            = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)
    title         = db.Column(db.String(200), nullable=False)
    description   = db.Column(db.Text, nullable=False)
    user_name     = db.Column(db.String(100), nullable=False)
    user_email    = db.Column(db.String(120), nullable=False)
    user_phone    = db.Column(db.String(30), nullable=True)
    department    = db.Column(db.String(100), nullable=True)
    category      = db.Column(db.String(50), nullable=False, default='other')
    priority      = db.Column(db.String(20), nullable=False, default='medium')
    status        = db.Column(db.String(20), nullable=False, default='open')
    assigned_to   = db.Column(db.String(100), nullable=True)
    resolution    = db.Column(db.Text, nullable=True)
    created_at    = db.Column(db.DateTime, default=now_local)
    updated_at    = db.Column(db.DateTime, default=now_local, onupdate=now_local)
    closed_at     = db.Column(db.DateTime, nullable=True)

    comments = db.relationship('Comment', backref='ticket', lazy=True, cascade='all, delete-orphan')


    def __repr__(self):
        return f'<Ticket {self.ticket_number}>'

    @property
    def priority_label(self):
        labels = {'low': 'Низкий', 'medium': 'Средний', 'high': 'Высокий', 'critical': 'Критический'}
        return labels.get(self.priority, self.priority)

    @property
    def status_label(self):
        labels = {'open': 'Открыто', 'in_progress': 'В работе', 'waiting': 'Ожидание', 'closed': 'Закрыто'}
        return labels.get(self.status, self.status)

    @property
    def category_label(self):
        labels = {
            'hardware': 'Оборудование',
            'software': 'Программное обеспечение',
            'network': 'Сеть / Передача данных',
            'access': 'Доступы и права',
            'other': 'Прочее'
        }
        return labels.get(self.category, self.category)


class Comment(db.Model):
    __tablename__ = 'comments'

    id          = db.Column(db.Integer, primary_key=True)
    ticket_id   = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    author      = db.Column(db.String(100), nullable=False)
    text        = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=now_local)

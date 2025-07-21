import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    
    # Налаштування автоматизації
    AUTO_UPDATE_INTERVAL = 3600  # секунди між автоматичними оновленнями
    BACKUP_INTERVAL = 86400  # секунди між бекапами (24 години)

# Статуси замовлень
ORDER_STATUSES = {
    'draft': 'Чернетка',
    'pending': 'Очікує підтвердження',
    'confirmed': 'Підтверджено',
    'in_progress': 'В роботі',
    'review': 'На перевірці',
    'revision': 'Потребує правок',
    'completed': 'Завершено',
    'cancelled': 'Скасовано'
}

# Кольори для статусів (для адмін панелі)
STATUS_COLORS = {
    'draft': '⚪',
    'pending': '🟡',
    'confirmed': '🔵',
    'in_progress': '🟠',
    'review': '🟣',
    'revision': '🟠',
    'completed': '🟢',
    'cancelled': '🔴'
}

# Ціни за типи робіт
ORDER_TYPE_PRICES = {
    "coursework": {
        "label": "Курсова робота",
        "base": 1500,
        "per_page": 50
    },
    "labwork": {
        "label": "Лабораторна робота",
        "base": 300,
        "per_work": 100
    },
    "essay": {
        "label": "Реферат",
        "base": 500,
        "per_page": 30
    },
    "testwork": {
        "label": "Контрольна робота",
        "base": 400,
        "per_work": 80
    },
    "other": {
        "label": "Інше",
        "base": 200,
        "per_page": 40
    }
}

# Налаштування реферальної системи
REFERRAL_BONUS_PERCENT = 5  # Відсоток бонусу за реферала
REFERRAL_MIN_ORDER_AMOUNT = 500  # Мінімальна сума замовлення для бонусу

# Налаштування спам захисту
SPAM_LIMITS = {
    'order_creation': {'limit': 3, 'window': 10},  # 3 замовлення за 10 хвилин
    'support_message': {'limit': 5, 'window': 5},  # 5 повідомлень за 5 хвилин
    'feedback': {'limit': 2, 'window': 60},  # 2 відгуки за годину
}

# Налаштування нагадувань
REMINDER_TYPES = {
    'deadline_approaching': {
        'days_before': 3,
        'message': 'Нагадування: до дедлайну вашого замовлення залишилось 3 дні'
    },
    'order_confirmed': {
        'message': 'Ваше замовлення підтверджено! Менеджер зв\'яжеться з вами найближчим часом.'
    },
    'order_completed': {
        'message': 'Ваше замовлення завершено! Перевірте роботу та підтвердьте отримання.'
    }
}



# Обмеження файлів
MAX_FILES_PER_ORDER = 10
ALLOWED_FILE_TYPES = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'image/jpeg',
    'image/png',
    'image/gif'
] 
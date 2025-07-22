import re
from datetime import datetime, timedelta
from typing import Tuple, Optional, List

from aiogram import Bot
from aiogram.fsm.context import FSMContext
import logging

def is_command(text: str) -> bool:
    return isinstance(text, str) and text.strip().startswith("/")

COMMAND_INPUT = "COMMAND_INPUT"

def validate_phone(phone: str) -> Tuple[bool, str]:
    """Валідує номер телефону для України"""
    if not phone:
        return False, "Номер телефону не може бути порожнім"
    
    # Видаляємо всі символи крім цифр, +, (,)
    cleaned_phone = re.sub(r'[^\d+()]', '', phone)
    
    # Регулярний вираз для українських номерів
    # Допускає формати: +380xxxxxxxxx, 0xxxxxxxxx, 380xxxxxxxxx
    pattern = re.compile(r'^(?:\+?380|0)\d{9}$')
    
    if not pattern.match(cleaned_phone.replace('(', '').replace(')', '')):
        return False, "Невірний формат українського номера телефону. Приклади: +380991234567, 0991234567"
        
    return True, "OK"

def validate_email(email: str) -> Tuple[bool, str]:
    """Валідує email"""
    if not email:
        return False, "Email не може бути порожнім"
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Невірний формат email"
    
    return True, "OK"

def validate_deadline(deadline: str) -> Tuple[bool, str]:
    """Валідує дедлайн"""
    if not deadline:
        return False, "Дедлайн не може бути порожнім"
    
    if is_command(deadline):
        return None, COMMAND_INPUT

    # Спробуємо різні формати дат
    formats = [
        "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y",
        "%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"
    ]
    
    parsed_date = None
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(deadline, fmt)
            break
        except ValueError:
            continue
            
    if parsed_date is None:
        return False, "Невірний формат дати. Використовуйте формат ДД.ММ.РРРР, наприклад: 10.10.2010"

    if parsed_date.date() < datetime.now().date():
        return False, "Дедлайн не може бути в минулому Повторіть ввід у форматі ДД.ММ.РРРР"
    if parsed_date.date() > datetime.now().date() + timedelta(days=365*2): # Дозволимо до 2-х років
        return False, "Дедлайн не може бути більше двох років вперед Повторіть ввід у форматі ДД.ММ.РРРР"
        
    return True, "OK"

def validate_volume(volume: str) -> Tuple[bool, str]:
    """Валідує обсяг роботи"""
    if not volume:
        return False, "Обсяг не може бути порожнім"
    
    if is_command(volume):
        return None, COMMAND_INPUT

    # Шукаємо числа в тексті
    numbers = re.findall(r'\d+', volume)
    if not numbers:
        return False, "Обсяг повинен містити числове значення (наприклад: 15)"
    
    try:
        volume_num = int(numbers[0])
        if volume_num < 1:
            return False, "Обсяг повинен бути не менше 1"
        if volume_num > 5000: # Збільшимо ліміт
            return False, "Обсяг не може бути більше 5000"
        return True, "OK"
    except ValueError:
        return False, "Невірний формат обсягу. Вкажіть лише число."

def validate_topic(topic: str) -> Tuple[bool, str]:
    """Валідує тему роботи"""
    if not topic:
        return False, "Тема не може бути порожньою"
    
    if is_command(topic):
        return None, COMMAND_INPUT

    if len(topic) < 3:
        return False, "Тема занадто коротка (мінімум 3 символи)"
    
    if len(topic) > 500:
        return False, "Тема занадто довга (максимум 500 символів)"
    
    return True, "OK"

def validate_subject(subject: str) -> Tuple[bool, str]:
    """Валідує предмет"""
    if not subject:
        return False, "Предмет не може бути порожнім"
    
    if is_command(subject):
        return None, COMMAND_INPUT

    if len(subject) < 2:
        return False, "Предмет занадто короткий (мінімум 2 символи)"
    
    if len(subject) > 100:
        return False, "Предмет занадто довгий (максимум 100 символів)"
    
    return True, "OK"

def validate_requirements(requirements: str) -> Tuple[bool, str]:
    """Валідує вимоги"""
    if not requirements:
        return True, "OK"  # Вимоги можуть бути порожніми
    
    if is_command(requirements):
        return None, COMMAND_INPUT

    if len(requirements) > 2000:
        return False, "Вимоги занадто довгі (максимум 2000 символів)"
    
    return True, "OK"

def validate_promocode(code: str) -> Tuple[bool, str]:
    """Валідує промокод"""
    if not code:
        return True, "OK"  # Промокод може бути порожнім
    
    if is_command(code):
        return None, COMMAND_INPUT

    if len(code) < 3:
        return False, "Промокод занадто короткий"
    
    if len(code) > 20:
        return False, "Промокод занадто довгий"
    
    if not re.match(r'^[A-Z0-9_-]+$', code):
        return False, "Промокод може містити тільки ВЕЛИКІ літери, цифри, дефіси та підкреслення"
    
    return True, "OK"

def sanitize_text(text: str, max_length: int = 2000) -> str:
    """Очищує текст від небезпечних символів та обмежує довжину"""
    if not text:
        return ""
    
    # Видаляємо HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Обмежуємо довжину
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()

def validate_file_size(file_size: int, max_size_mb: int = 20) -> Tuple[bool, str]:
    """Валідує розмір файлу в мегабайтах"""
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        return False, f"Файл занадто великий. Максимальний розмір: {max_size_mb}MB"
    
    return True, "OK"

def validate_file_type(mime_type: str, allowed_types: list = None) -> Tuple[bool, str]:
    """Валідує тип файлу"""
    if allowed_types is None:
        allowed_types = [
            'application/pdf', 'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain', 'image/jpeg', 'image/png', 'application/zip', 'application/x-rar-compressed'
        ]
        
    if mime_type not in allowed_types:
        return False, f"Непідтримуваний тип файлу: {mime_type}"
    
    return True, "OK" 

async def delete_previous_messages(bot: Bot, chat_id: int, state: FSMContext, keys: List[str] = None):
    """
    Видаляє всі попередні повідомлення (бота і користувача) для поточного чату.
    За замовчуванням шукає ключі last_bot_message_id, last_user_message_id, last_message_ids у state.
    """
    data = await state.get_data()
    if keys is None:
        keys = ["last_bot_message_id", "last_user_message_id", "last_message_ids"]
    message_ids = set()
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            message_ids.update(value)
        elif isinstance(value, int):
            message_ids.add(value)
        elif isinstance(value, str):
            try:
                message_ids.add(int(value))
            except Exception:
                pass
    for message_id in message_ids:
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception:
            pass  # Ігноруємо помилки (наприклад, якщо вже видалено) 

async def delete_all_tracked_messages(bot: Bot, chat_id: int, state: FSMContext, keys: list = None):
    """
    Видаляє останнє повідомлення бота (last_bot_message_id) і користувача (last_user_message_id) для максимально чистого чату.
    """
    data = await state.get_data()
    if keys is None:
        keys = ["last_bot_message_id", "last_user_message_id"]
    message_ids = set()
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            message_ids.update(value)
        elif isinstance(value, int):
            message_ids.add(value)
        elif isinstance(value, str):
            try:
                message_ids.add(int(value))
            except Exception:
                pass
    for message_id in message_ids:
        try:
            await bot.delete_message(chat_id, message_id)
            print(f"[delete_all_tracked_messages] Видалено повідомлення {message_id}")
        except Exception as e:
            print(f"[delete_all_tracked_messages] Не вдалося видалити {message_id}: {e}")
    # Очищаємо ключі у state
    await state.update_data(last_bot_message_id=None, last_user_message_id=None) 
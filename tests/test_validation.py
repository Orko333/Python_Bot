import pytest
from app.utils.validation import (
    validate_phone, validate_email, validate_deadline,
    validate_volume, validate_topic, validate_subject,
    validate_requirements, validate_promocode,
    sanitize_text, validate_file_size, validate_file_type
)

def test_validate_phone():
    """Тест валідації номера телефону"""
    # Валідні номери
    assert validate_phone("+380991234567")[0] is True
    assert validate_phone("0991234567")[0] is True
    assert validate_phone("380991234567")[0] is True
    
    # Невалідні номери
    assert validate_phone("")[0] is False  # Порожній
    assert validate_phone("123")[0] is False  # Закороткий
    assert validate_phone("a123456789")[0] is False  # З буквами
    assert validate_phone("+" + "1" * 20)[0] is False  # Задовгий

def test_validate_email():
    """Тест валідації email"""
    # Валідні email
    assert validate_email("test@example.com")[0] is True
    assert validate_email("user.name@domain.co.uk")[0] is True
    assert validate_email("user+tag@domain.com")[0] is True
    
    # Невалідні email
    assert validate_email("")[0] is False  # Порожній
    assert validate_email("test")[0] is False  # Без @
    assert validate_email("test@")[0] is False  # Без домену
    assert validate_email("@domain.com")[0] is False  # Без імені
    assert validate_email("test@domain")[0] is False  # Без TLD

def test_validate_deadline():
    """Тест валідації дедлайну"""
    from datetime import datetime, timedelta

    future = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    past = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    too_far = (datetime.now() + timedelta(days=800)).strftime("%Y-%m-%d")  # >2 роки

    # Валідні дедлайни
    assert validate_deadline(future)[0] is True
    assert validate_deadline("2025-12-31")[0] is True # Майбутня дата

    # Невалідні дедлайни
    assert validate_deadline(past)[0] is False # Минула дата
    assert validate_deadline(too_far)[0] is False # Занадто далека дата
    assert validate_deadline("invalid-date")[0] is False

def test_validate_volume():
    """Тест валідації обсягу"""
    # Валідні обсяги
    assert validate_volume("10")[0] is True
    assert validate_volume("100 сторінок")[0] is True
    assert validate_volume("50 робіт")[0] is True
    
    # Невалідні обсяги
    assert validate_volume("")[0] is False  # Порожній
    assert validate_volume("zero")[0] is False  # Без чисел
    assert validate_volume("0")[0] is False  # Нуль
    assert validate_volume("5001")[0] is False  # Завеликий

def test_validate_topic():
    """Тест валідації теми"""
    # Валідні теми
    assert validate_topic("Test Topic")[0] is True
    assert validate_topic("A" * 100)[0] is True
    
    # Невалідні теми
    assert validate_topic("")[0] is False  # Порожня
    assert validate_topic("ab")[0] is False  # Закоротка
    assert validate_topic("A" * 501)[0] is False  # Задовга

def test_validate_subject():
    """Тест валідації предмету"""
    # Валідні предмети
    assert validate_subject("Math")[0] is True
    assert validate_subject("A" * 50)[0] is True
    
    # Невалідні предмети
    assert validate_subject("")[0] is False  # Порожній
    assert validate_subject("a")[0] is False  # Закороткий
    assert validate_subject("A" * 101)[0] is False  # Задовгий

def test_validate_requirements():
    """Тест валідації вимог"""
    # Валідні вимоги
    assert validate_requirements("")[0] is True  # Можуть бути порожніми
    assert validate_requirements("Test requirements")[0] is True
    assert validate_requirements("A" * 1000)[0] is True
    
    # Невалідні вимоги
    assert validate_requirements("A" * 2001)[0] is False  # Задовгі

def test_validate_promocode():
    """Тест валідації промокоду"""
    # Валідні промокоди
    assert validate_promocode("")[0] is True  # Може бути порожнім
    assert validate_promocode("TEST2024")[0] is True
    assert validate_promocode("SUMMER-50")[0] is True
    assert validate_promocode("BLACK_FRIDAY")[0] is True
    
    # Невалідні промокоди
    assert validate_promocode("te")[0] is False  # Закороткий
    assert validate_promocode("A" * 21)[0] is False  # Задовгий
    assert validate_promocode("test@code")[0] is False  # Заборонені символи

def test_sanitize_text():
    """Тест санітизації тексту"""
    # Перевірка видалення HTML
    assert "<b>" not in sanitize_text("<b>test</b>")
    assert "<script>" not in sanitize_text("<script>alert(1)</script>")
    
    # Перевірка обмеження довжини
    long_text = "A" * 6000
    assert len(sanitize_text(long_text)) <= 5000
    
    # Перевірка очищення пробілів
    assert sanitize_text("  test  ") == "test"
    assert sanitize_text("\ntest\n") == "test"

def test_validate_file_size():
    """Тест валідації розміру файлу"""
    max_size = 20 * 1024 * 1024  # 20MB
    
    # Валідні розміри
    assert validate_file_size(1024)[0] is True  # 1KB
    assert validate_file_size(max_size)[0] is True  # Максимальний розмір
    
    # Невалідні розміри
    assert validate_file_size(max_size + 1)[0] is False  # Більше максимуму

def test_validate_file_type():
    """Тест валідації типу файлу"""
    allowed_types = ['application/pdf', 'image/jpeg']
    
    # Валідні типи
    assert validate_file_type('application/pdf', allowed_types)[0] is True
    assert validate_file_type('image/jpeg', allowed_types)[0] is True
    
    # Невалідні типи
    assert validate_file_type('image/gif', allowed_types)[0] is False
    assert validate_file_type('application/exe', allowed_types)[0] is False 
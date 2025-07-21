import pytest
import pytest_asyncio
import os
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import Config
from app import db as db_module # Перейменовуємо, щоб уникнути конфлікту імен
from app.db import init_db
from unittest.mock import AsyncMock
from aiogram import types
from datetime import datetime, timedelta

@pytest_asyncio.fixture(scope="function")
async def db_connection(monkeypatch):
    """Створює з'єднання з БД в пам'яті для кожного тесту."""
    conn = sqlite3.connect(":memory:")
    # Патчимо функцію get_db_connection, щоб вона повертала наше з'єднання
    monkeypatch.setattr(db_module, 'get_db_connection', lambda: conn)
    init_db() # Ініціалізуємо схему в цій БД
    yield conn
    conn.close()

@pytest_asyncio.fixture(scope="function")
async def bot():
    """Створює мок бота."""
    return AsyncMock(spec=Bot)

@pytest_asyncio.fixture
async def dp(bot):
    """Створює тестовий диспетчер."""
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    return dp

@pytest_asyncio.fixture
async def admin_user():
    """Повертає тестового адміністратора."""
    return types.User(
        id=Config.ADMIN_IDS[0] if Config.ADMIN_IDS else 999999,
        is_bot=False,
        username='test_admin',
        first_name='Test Admin'
    )

@pytest_asyncio.fixture
async def regular_user():
    """Повертає звичайного тестового користувача."""
    return types.User(
        id=123456789,
        is_bot=False,
        username='test_user',
        first_name='Test User'
    )

@pytest_asyncio.fixture
async def message(regular_user):
    """Створює мок повідомлення з реальним користувачем."""
    message = AsyncMock(spec=types.Message)
    message.from_user = regular_user
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    return message

@pytest_asyncio.fixture
async def state():
    """Створює мок стану."""
    return AsyncMock()

@pytest_asyncio.fixture
async def callback_query(regular_user, message):
    """Створює мок callback query."""
    callback = AsyncMock(spec=types.CallbackQuery)
    callback.from_user = regular_user
    callback.message = message
    callback.answer = AsyncMock()
    return callback

@pytest.fixture
def test_order():
    """Повертає тестове замовлення."""
    return {
        'user_id': 123456789,
        'first_name': 'Test User',
        'username': 'test_user',
        'phone_number': '+380991234567',
        'type_label': 'Курсова робота',
        'order_type': 'coursework',
        'topic': 'Test Topic',
        'subject': 'Test Subject',
        'deadline': (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
        'volume': '30',
        'requirements': 'Test Requirements',
        'files': ['test_file_id'],
        'price': 1000
    }

@pytest.fixture
def test_promocode():
    """Повертає тестовий промокод."""
    return {
        'code': 'TEST2024',
        'discount_type': 'percent',
        'discount_value': 10,
        'usage_limit': 100,
        'expires_at': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S'),
        'is_personal': False,
        'personal_user_id': None,
        'min_order_amount': 500
    }

@pytest.fixture
def test_feedback():
    """Повертає тестовий відгук."""
    return {
        'user_id': 123456789,
        'username': 'test_user',
        'text': 'Test Feedback',
        'stars': 5
    } 
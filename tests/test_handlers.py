import pytest
from unittest.mock import AsyncMock, Mock, ANY
from aiogram import types
from aiogram.fsm.context import FSMContext
from app.handlers.order import OrderStates, order_handler, process_topic, process_file_upload, confirm_order_callback, process_subject, process_requirements, process_file_text
from app.handlers.cabinet import cabinet_handler
from app.handlers.feedback import feedback_start
from app.config import Config
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from app.handlers.order import get_back_keyboard
from app.handlers.cabinet import get_admin_keyboard
from app.handlers.help import help_handler
from app.handlers.support import support_start
from app.handlers.feedback import feedback_start
from app.handlers.cabinet import admin_stats_callback, admin_broadcast_callback, admin_backup_callback, admin_promos_callback, promo_stats_callback, BroadcastStates
from app.handlers.support import support_user_message
from app.config import Config
from aiogram import Bot


pytestmark = pytest.mark.asyncio

async def test_order_handler(message, state):
    # Цей обробник насправді не встановлює стан, а лише відповідає
    # Тому ми перевіряємо, що він був викликаний
    await order_handler(message, state)
    message.answer.assert_called_once()

async def test_process_topic(message, state):
    message.text = "Test Topic"
    message.chat = Mock()
    message.chat.id = 123
    message.bot = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    await process_topic(message, state)
    state.update_data.assert_any_call(topic="Test Topic")
    state.set_state.assert_any_call(OrderStates.waiting_for_subject)
    message.answer.assert_called()

async def test_process_file_upload(message, state):
    document = types.Document(file_id="test_file_id", file_unique_id="test_unique_id", file_size=1024, mime_type="application/pdf")
    message.document = document
    message.chat = Mock()
    message.chat.id = 123
    message.bot = AsyncMock()
    state.get_data = AsyncMock(return_value={'files': []})
    state.update_data = AsyncMock()
    await process_file_upload(message, state)
    state.update_data.assert_any_call(files=["test_file_id"])
    message.answer.assert_called()

async def test_cabinet_handler(message, admin_user, state):
    message.from_user = admin_user
    message.chat = Mock()
    message.chat.id = 123
    message.bot = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    await cabinet_handler(message, state)
    message.answer.assert_called()
    # Далі можна додати перевірку тексту, якщо потрібно

async def test_feedback_start(message, state):
    message.chat = Mock()
    message.chat.id = 123
    message.bot = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    await feedback_start(message, state)
    message.answer.assert_called()



def test_get_back_keyboard():
    kb = get_back_keyboard()
    assert isinstance(kb, ReplyKeyboardMarkup)
    buttons = [btn.text for row in kb.keyboard for btn in row]
    assert "🔙 Назад" in buttons
    assert "❌ Скасувати" in buttons

def test_get_admin_keyboard():
    kb = get_admin_keyboard()
    assert isinstance(kb, InlineKeyboardMarkup)
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "📊 Статистика" in texts or any("Статистика" in t for t in texts)
    assert "📢 Масові розсилки" in texts
    assert "💾 Створити бекап" in texts
    assert "🎫 Управління промокодами" in texts
    assert "🔧 Налаштування" in texts

# Тест для markup у start_handler
from app.handlers.start import start_handler
from aiogram.fsm.context import FSMContext
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_start_handler_markup():
    message = AsyncMock()
    message.text = "/start"
    message.from_user.id = 123
    state = AsyncMock(spec=FSMContext)
    await start_handler(message, state)
    args, kwargs = message.answer.call_args
    reply_markup = kwargs["reply_markup"]
    assert isinstance(reply_markup, InlineKeyboardMarkup)
    assert reply_markup.inline_keyboard[0][0].text == "Зробити замовлення"
    assert reply_markup.inline_keyboard[0][0].callback_data.startswith("order_type:") 

@pytest.mark.asyncio
async def test_help_handler_markup():
    message = AsyncMock()
    message.from_user.id = 123
    state = AsyncMock()
    await help_handler(message, state)
    message.answer.assert_called()
    args, kwargs = message.answer.call_args
    assert "Доступні команди" in args[0]
    assert kwargs["parse_mode"] == "HTML"

@pytest.mark.asyncio
async def test_support_start_markup():
    message = AsyncMock()
    state = AsyncMock()
    await support_start(message, state)
    message.answer.assert_called()
    args, kwargs = message.answer.call_args
    assert "питання" in args[0].lower()

@pytest.mark.asyncio
async def test_feedback_start_markup():
    message = AsyncMock()
    state = AsyncMock()
    await feedback_start(message, state)
    message.answer.assert_called()
    args, kwargs = message.answer.call_args
    assert "відгук" in args[0].lower()

# Тест для markup у order_handler
from app.handlers.order import order_handler
@pytest.mark.asyncio
async def test_order_handler_markup():
    message = AsyncMock()
    message.from_user.id = 123
    state = AsyncMock(spec=FSMContext)
    message.text = "/order"
    await order_handler(message, state)
    message.answer.assert_called()
    args, kwargs = message.answer.call_args
    reply_markup = kwargs["reply_markup"]
    assert isinstance(reply_markup, InlineKeyboardMarkup)
    assert any("order_type:" in btn.callback_data for row in reply_markup.inline_keyboard for btn in row) 

@pytest.mark.asyncio
async def test_order_fsm_back_cancel(monkeypatch):
    # Тест кнопки 'Назад' у process_topic
    message = AsyncMock()
    message.text = "🔙 Назад"
    message.chat = Mock()
    message.chat.id = 123
    message.bot = AsyncMock()
    state = AsyncMock()
    state.clear = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.set_state = AsyncMock()
    await process_topic(message, state)
    message.answer.assert_called_with("Оберіть тип роботи:", reply_markup=ANY)
    state.set_state.assert_called_with(OrderStates.waiting_for_type)

    # Тест кнопки 'Скасувати' у process_topic
    message = AsyncMock()
    message.text = "❌ Скасувати"
    message.chat = Mock()
    message.chat.id = 123
    message.bot = AsyncMock()
    state = AsyncMock()
    state.clear = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.set_state = AsyncMock()
    await process_topic(message, state)
    message.answer.assert_called_with("Створення замовлення скасовано.", reply_markup=ANY)
    state.clear.assert_called()

    # Тест кнопки 'Назад' у process_subject
    message = AsyncMock()
    message.text = "🔙 Назад"
    state = AsyncMock()
    await process_subject(message, state)
    message.answer.assert_called_with("Введіть тему роботи:", reply_markup=ANY)
    state.set_state.assert_called_with(ANY)

    # Тест кнопки 'Скасувати' у process_subject
    message = AsyncMock()
    message.text = "❌ Скасувати"
    state = AsyncMock()
    await process_subject(message, state)
    message.answer.assert_called_with("Створення замовлення скасовано.", reply_markup=ANY)
    state.clear.assert_called_once()

    # Тест кнопки 'Назад' у process_requirements
    message = AsyncMock()
    message.text = "🔙 Назад"
    state = AsyncMock()
    await process_requirements(message, state)
    message.answer.assert_called_with("Введіть обсяг роботи:", reply_markup=ANY)
    state.set_state.assert_called_with(ANY)

    # Тест кнопки 'Скасувати' у process_requirements
    message = AsyncMock()
    message.text = "❌ Скасувати"
    state = AsyncMock()
    await process_requirements(message, state)
    message.answer.assert_called_with("Створення замовлення скасовано.", reply_markup=ANY)
    state.clear.assert_called_once()

@pytest.mark.asyncio
async def test_admin_stats_callback():
    callback = AsyncMock()
    callback.from_user.id = 1
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    from app.config import Config
    Config.ADMIN_IDS = [1]
    await admin_stats_callback(callback)
    callback.message.edit_text.assert_called()
    callback.answer.assert_called()

@pytest.mark.asyncio
async def test_admin_broadcast_callback():
    callback = AsyncMock()
    callback.from_user.id = 1
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    state = AsyncMock()
    from app.config import Config
    Config.ADMIN_IDS = [1]
    await admin_broadcast_callback(callback, state)
    callback.message.edit_text.assert_called()
    callback.answer.assert_called()
    state.set_state.assert_called_with(BroadcastStates.waiting_for_message)

@pytest.mark.asyncio
async def test_admin_backup_callback():
    callback = AsyncMock()
    callback.from_user.id = 1
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    from app.config import Config
    Config.ADMIN_IDS = [1]
    await admin_backup_callback(callback)
    callback.message.edit_text.assert_called()
    callback.answer.assert_called()

@pytest.mark.asyncio
async def test_admin_promos_callback():
    callback = AsyncMock()
    callback.from_user.id = 1
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    from app.config import Config
    Config.ADMIN_IDS = [1]
    await admin_promos_callback(callback)
    callback.message.edit_text.assert_called()
    callback.answer.assert_called()

@pytest.mark.asyncio
async def test_promo_stats_callback():
    callback = AsyncMock()
    callback.from_user.id = 1
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    callback.message.chat = Mock()
    callback.message.chat.id = 123
    callback.bot = AsyncMock()
    from app.config import Config
    Config.ADMIN_IDS = [1]
    await promo_stats_callback(callback)
    callback.message.edit_text.assert_called() 
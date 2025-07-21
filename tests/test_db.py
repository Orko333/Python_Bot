import pytest
from datetime import datetime
from app.db import (
    add_order, get_order_by_id, update_order,
    add_promocode, is_promocode_valid, use_promocode,
    add_feedback, get_feedbacks,
    add_referral_bonus, get_referrals,
    add_reminder, get_pending_reminders, mark_reminder_sent,
    check_spam_protection, get_promocode, add_referral
)

# Використовуємо pytest.mark.asyncio для всіх тестів
pytestmark = pytest.mark.asyncio

async def test_add_and_get_order(db_connection, test_order):
    order_id = add_order(**test_order)
    assert order_id > 0
    order_data = get_order_by_id(order_id)
    assert order_data is not None
    assert order_data['order'][1] == test_order['user_id']

async def test_update_order(db_connection, test_order):
    order_id = add_order(**test_order)
    update_order(order_id, status='confirmed')
    order_data = get_order_by_id(order_id)
    assert order_data['order'][14] == 'confirmed'

async def test_promocode_operations(db_connection, test_promocode):
    add_promocode(**test_promocode)
    promo_from_db = get_promocode(test_promocode['code'])
    is_valid, message = is_promocode_valid(promo_from_db, 12345, test_promocode['min_order_amount'] + 100)
    assert is_valid is True, f"Промокод не пройшов валідацію: {message}"
    
    discount = use_promocode(test_promocode['code'], 12345, 1, 100)
    assert discount > 0

async def test_feedback_operations(db_connection, test_feedback):
    # Виправляємо передачу аргументів
    add_feedback(test_feedback)
    feedbacks = get_feedbacks()
    assert len(feedbacks) > 0
    assert feedbacks[0][1] == test_feedback['user_id']

async def test_referral_operations(db_connection, test_order):
    # Спочатку створюємо реферальний зв'язок
    add_referral(987654321, test_order['user_id'])
    
    order_id = add_order(**test_order)
    add_referral_bonus(test_order['user_id'], 987654321, order_id, 100)
    referrals = get_referrals(987654321)
    assert len(referrals) > 0

async def test_reminder_operations(db_connection):
    now_iso = datetime.now().isoformat()
    add_reminder(123, 1, 'test', now_iso, "Test message")
    reminders = get_pending_reminders()
    assert len(reminders) > 0
    mark_reminder_sent(reminders[0][0])
    new_reminders = get_pending_reminders()
    assert len(new_reminders) < len(reminders)

async def test_spam_protection(db_connection):
    user_id = 12345
    action = 'test_spam'
    limit = 2
    assert check_spam_protection(user_id, action, limit, 1) is True
    assert check_spam_protection(user_id, action, limit, 1) is True
    # Третій запит має бути заблокований
    assert check_spam_protection(user_id, action, limit, 1) is False 
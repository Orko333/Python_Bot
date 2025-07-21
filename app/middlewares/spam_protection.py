from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from app.db import check_spam_protection
from app.config import SPAM_LIMITS
import logging

logger = logging.getLogger(__name__)

class SpamProtectionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        
        # Визначаємо тип дії
        action_type = "general"
        
        if isinstance(event, Message):
            if event.text and event.text.startswith('/order'):
                action_type = "order_creation"
            elif event.text and event.text.startswith('/support'):
                action_type = "support_message"
            elif event.text and event.text.startswith('/feedback'):
                action_type = "feedback"
        elif isinstance(event, CallbackQuery):
            if event.data and event.data.startswith('order_type:'):
                action_type = "order_creation"
        
        # Перевіряємо спам захист
        if action_type in SPAM_LIMITS:
            limit = SPAM_LIMITS[action_type]['limit']
            window = SPAM_LIMITS[action_type]['window']
            
            if not check_spam_protection(user_id, action_type, limit, window):
                if isinstance(event, Message):
                    await event.answer(
                        f"⚠️ Занадто багато запитів. Спробуйте через {window} хвилин."
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        f"⚠️ Занадто багато запитів. Спробуйте через {window} хвилин.",
                        show_alert=True
                    )
                return
        
        # Якщо все добре, продовжуємо обробку
        return await handler(event, data) 
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
from app.db import get_pending_reminders, mark_reminder_sent, get_orders, update_order_status
from app.config import Config, REMINDER_TYPES
import logging

logger = logging.getLogger(__name__)

class AutomationService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
    
    async def start(self):
        """Запускає автоматизацію"""
        self.is_running = True
        logger.info("Автоматизація запущена")
        
        while self.is_running:
            try:
                await self.process_reminders()
                await self.process_deadline_reminders()
                await self.process_auto_status_updates()
                await asyncio.sleep(Config.AUTO_UPDATE_INTERVAL)
            except Exception as e:
                logger.error(f"Помилка в автоматизації: {e}")
                await asyncio.sleep(60)  # Чекаємо хвилину перед повторною спробою
    
    async def stop(self):
        """Зупиняє автоматизацію"""
        self.is_running = False
        logger.info("Автоматизація зупинена")
    
    async def process_reminders(self):
        """Обробляє нагадування"""
        reminders = get_pending_reminders()
        
        for reminder in reminders:
            try:
                reminder_id, user_id, order_id, reminder_type, scheduled_at, sent_at, message = reminder
                
                # Відправляємо нагадування
                await self.bot.send_message(user_id, message)
                
                # Позначаємо як відправлене
                mark_reminder_sent(reminder_id)
                
                logger.info(f"Нагадування {reminder_id} відправлено користувачу {user_id}")
                
            except Exception as e:
                logger.error(f"Помилка при відправці нагадування {reminder_id}: {e}")
    
    async def process_deadline_reminders(self):
        """Створює нагадування про дедлайни"""
        orders = get_orders(status='confirmed')
        
        for order in orders:
            try:
                order_id, user_id, _, _, _, _, _, _, _, deadline, _, _, _, _, _, _, _, _, _, _ = order
                
                # Парсимо дедлайн
                deadline_date = self.parse_deadline(deadline)
                if not deadline_date:
                    continue
                
                # Перевіряємо чи потрібно створити нагадування
                days_before = REMINDER_TYPES['deadline_approaching']['days_before']
                reminder_date = deadline_date - timedelta(days=days_before)
                
                if datetime.now().date() == reminder_date:
                    # Створюємо нагадування
                    message = REMINDER_TYPES['deadline_approaching']['message']
                    scheduled_at = datetime.now().isoformat()
                    
                    from app.db import add_reminder
                    add_reminder(user_id, order_id, 'deadline_approaching', scheduled_at, message)
                    
                    logger.info(f"Створено нагадування про дедлайн для замовлення {order_id}")
                
            except Exception as e:
                logger.error(f"Помилка при обробці дедлайну замовлення {order_id}: {e}")
    
    async def process_auto_status_updates(self):
        """Автоматично оновлює статуси замовлень"""
        orders = get_orders(status='in_progress')
        
        for order in orders:
            try:
                order_id, user_id, _, _, _, _, _, _, _, deadline, _, _, _, _, _, _, _, _, _, _ = order
                
                # Парсимо дедлайн
                deadline_date = self.parse_deadline(deadline)
                if not deadline_date:
                    continue
                
                # Якщо дедлайн минув, змінюємо статус на "review"
                if datetime.now().date() > deadline_date:
                    update_order_status(order_id, 'review', notes="Автоматичне оновлення: дедлайн минув")
                    
                    # Сповіщаємо користувача
                    await self.bot.send_message(
                        user_id,
                        f"ℹ️ Ваше замовлення #{order_id} переведено на перевірку (дедлайн минув)."
                    )
                    
                    logger.info(f"Автоматично оновлено статус замовлення {order_id} на 'review'")
                
            except Exception as e:
                logger.error(f"Помилка при автоматичному оновленні статусу замовлення {order_id}: {e}")
    
    def parse_deadline(self, deadline_str):
        """Парсить дедлайн з різних форматів"""
        try:
            # Спробуємо різні формати
            formats = [
                "%Y-%m-%d",
                "%d.%m.%Y",
                "%d/%m/%Y",
                "%d-%m-%Y"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(deadline_str, fmt).date()
                except ValueError:
                    continue
            
            # Якщо не вдалося розпарсити, спробуємо знайти числа
            import re
            numbers = re.findall(r'\d+', deadline_str)
            if len(numbers) >= 3:
                # Припускаємо формат DD.MM.YYYY
                day, month, year = int(numbers[0]), int(numbers[1]), int(numbers[2])
                if year < 100:  # Якщо рік двозначний
                    year += 2000
                return datetime(year, month, day).date()
            
            return None
            
        except Exception:
            return None
    
    async def send_auto_response(self, user_id, message_type):
        """Відправляє автоматичні відповіді"""
        auto_responses = {
            'greeting': "👋 Вітаю! Чим можу допомогти? Використайте /help для списку команд.",
            'pricing': "💰 Детальну інформацію про ціни можна отримати командою /prices",
            'deadline': "⏰ Терміни виконання залежать від складності роботи. Зазвичай від 3 до 14 днів.",
            'payment': "💳 Оплата відбувається у два етапи: 50% передоплати та 50% після завершення.",
            'quality': "✅ Ми гарантуємо якість роботи та безкоштовні правки протягом гарантійного періоду."
        }
        
        if message_type in auto_responses:
            await self.bot.send_message(user_id, auto_responses[message_type])

# Глобальний екземпляр сервісу
automation_service = None

async def start_automation(bot: Bot):
    """Запускає автоматизацію"""
    global automation_service
    automation_service = AutomationService(bot)
    asyncio.create_task(automation_service.start())

async def stop_automation():
    """Зупиняє автоматизацію"""
    global automation_service
    if automation_service:
        await automation_service.stop() 
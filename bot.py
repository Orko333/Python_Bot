import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.config import Config
from app.handlers import (
    start_router, help_router, order_router, 
    cabinet_router, support_router, feedback_router, 
    faq_router, prices_router, broadcast_router
)
from app.handlers.main_commands import router as main_commands_router, setup_bot_commands
from app.db import init_db
from app.services.automation import start_automation, stop_automation

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    try:
        # Ініціалізуємо базу даних
        init_db()
        logger.info("База даних ініціалізована")
        
        # Створюємо бота та диспетчер
        bot = Bot(token=Config.BOT_TOKEN)
        dp = Dispatcher()
        
        # Налаштовуємо команди бота
        await setup_bot_commands(bot)
        logger.info("Команди бота налаштовані")
        
        # Реєструємо роутери в порядку пріоритету
        dp.include_router(main_commands_router)
        dp.include_router(start_router)
        dp.include_router(help_router)
        dp.include_router(faq_router)
        dp.include_router(prices_router)
        dp.include_router(order_router)
        dp.include_router(cabinet_router)
        dp.include_router(support_router)
        dp.include_router(feedback_router)
        dp.include_router(broadcast_router)
        
        logger.info("Всі роутери зареєстровані")
        
        # Запускаємо автоматизацію
        await start_automation(bot)
        logger.info("Автоматизація запущена")
        
        # Запускаємо бота
        logger.info("Бот запускається...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Помилка запуску бота: {e}")
        raise
    finally:
        # Зупиняємо автоматизацію при завершенні
        await stop_automation()
        logger.info("Бот зупинено")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"Критична помилка: {e}") 
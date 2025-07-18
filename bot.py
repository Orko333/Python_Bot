import asyncio
from aiogram import Bot, Dispatcher
from app.config import Config
from app.handlers import start, help as help_handler, order, cabinet, support, feedback
from app.db import init_db

async def main():
    init_db()
    bot = Bot(token=Config.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(help_handler.router)
    dp.include_router(order.router)
    dp.include_router(cabinet.router)
    dp.include_router(support.router)
    dp.include_router(feedback.router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 
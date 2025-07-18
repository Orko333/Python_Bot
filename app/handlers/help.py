from aiogram import types, Router
from aiogram.filters import Command
from app.config import Config

router = Router()

@router.message(Command("help"))
async def help_handler(message: types.Message):
    user_id = message.from_user.id
    text = (
        "<b>Доступні команди:</b>\n"
        "/start — Головне меню\n"
        "/order — Зробити нове замовлення\n"
        "/cabinet — Мої замовлення\n"
        "/myref — Моя реферальна система\n"
        "/feedback — Залишити відгук\n"
        "/privacy — Політика конфіденційності\n"
        "/disclaimer — Відмова від відповідальності\n"
        "/support — Зв'язок з менеджером\n"
    )
    if user_id in Config.ADMIN_IDS:
        text += (
            "\n<b>Для адміністраторів:</b>\n"
            "/orders — Всі замовлення\n"
            "/order_[номер] — Переглянути деталі замовлення (наприклад: /order_5)\n"
            "/setstatus_[номер]_[статус] — Змінити статус замовлення (наприклад: /setstatus_5_done)\n"
            "/stats — Статистика\n"
            "/addpromo_[код]_[тип]_[значення]_[ліміт] — Додати промокод (наприклад: /addpromo_SUMMER2024_percent_10_100)\n"
            "/promos — Статистика промокодів\n"
            "/feedbacks — Всі відгуки\n"
        )
    await message.answer(text, parse_mode="HTML") 
from aiogram import types, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.db import add_referral, get_referrals

router = Router()

ORDER_TYPES = [
    ("Курсова робота", "coursework"),
    ("Лабораторна робота", "labwork"),
    ("Реферат", "essay"),
    ("Контрольна робота", "testwork"),
    ("Інше", "other")
]

@router.message(Command("start"))
async def start_handler(message: types.Message):
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref"):
        try:
            ref_id = int(args[1][3:])
            if ref_id != message.from_user.id:
                add_referral(ref_id, message.from_user.id)
        except Exception:
            pass
    text = (
        "👋 <b>Вітаю у боті для замовлення студентських робіт!</b>\n\n"
        "Тут ти можеш швидко та зручно замовити курсову, лабораторну, реферат чи іншу роботу.\n\n"
        "<b>Як це працює?</b>\n"
        "1️⃣ Натисни /order або кнопку нижче\n"
        "2️⃣ Обери тип роботи\n"
        "3️⃣ Заповни коротку форму\n"
        "4️⃣ Отримай орієнтовну ціну та підтверди замовлення\n\n"
        "Після підтвердження з тобою зв'яжеться менеджер.\n"
        "Якщо є питання — скористайся командою /help."
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Зробити замовлення", callback_data="order_type:coursework")]
        ]
    )
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@router.message(Command("order"))
async def order_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"order_type:{code}")]
            for name, code in ORDER_TYPES
        ]
    )
    await message.answer("Оберіть тип роботи:", reply_markup=keyboard)

@router.message(Command("privacy"))
async def privacy_handler(message: types.Message):
    text = (
        "<b>Політика конфіденційності</b>\n\n"
        "Ми зберігаємо лише ті дані, які необхідні для виконання вашого замовлення: ім'я, username, номер телефону, деталі замовлення.\n"
        "Дані не передаються третім особам, окрім випадків, передбачених законом.\n"
        "Ви можете звернутися до адміністратора для видалення своїх даних.\n"
        "Використовуючи цього бота, ви погоджуєтесь з цією політикою."
    )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("disclaimer"))
async def disclaimer_handler(message: types.Message):
    text = (
        "<b>Відмова від відповідальності</b>\n\n"
        "Бот є лише посередником між замовником і виконавцем.\n"
        "Адміністрація не несе відповідальності за якість виконання робіт, строки та інші зобов'язання, якщо інше не обумовлено окремо.\n"
        "Всі питання щодо виконання замовлення вирішуються напряму з менеджером."
    )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("myref"))
async def myref_handler(message: types.Message):
    user_id = message.from_user.id
    ref_link = f"https://t.me/{(await message.bot.me()).username}?start=ref{user_id}"
    referrals = get_referrals(user_id)
    text = (
        f"<b>Твоє реферальне посилання:</b>\n{ref_link}\n\n"
        f"Запрошено користувачів: <b>{len(referrals)}</b>"
    )
    await message.answer(text, parse_mode="HTML") 
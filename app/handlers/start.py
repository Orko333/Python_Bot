from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
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
async def start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        await state.clear()
        data = await state.get_data()
        last_info_id = data.get('last_info_message_id')
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        print(f"[INFO] /start: user {user_id} - state cleared")
        # Handle referral logic
        args = message.text.split()
        if len(args) > 1 and args[1].startswith("ref"):
            try:
                ref_id = int(args[1][3:])
                if ref_id != user_id:
                    add_referral(ref_id, user_id)
                    print(f"[INFO] /start: user {user_id} - referral from {ref_id}")
            except Exception as e:
                print(f"[ERROR] /start: user {user_id} - referral parse error: {e}")
        # Send welcome message
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
        sent = await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        await state.update_data(last_info_message_id=sent.message_id)
        print(f"[INFO] /start: user {user_id} - welcome sent")
    except Exception as e:
        data = await state.get_data()
        last_info_id = data.get('last_info_message_id')
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        print(f"[ERROR] /start: user {user_id} - {e}")
        sent = await message.answer("Сталася помилка при старті.")
        await state.update_data(last_info_message_id=sent.message_id)

@router.message(Command("privacy"))
async def privacy_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        data = await state.get_data()
        last_info_id = data.get('last_info_message_id')
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        text = (
            "<b>Політика конфіденційності</b>\n\n"
            "Ми зберігаємо лише ті дані, які необхідні для виконання вашого замовлення: ім'я, username, номер телефону, деталі замовлення.\n"
            "Дані не передаються третім особам, окрім випадків, передбачених законом.\n"
            "Ви можете звернутися до адміністратора для видалення своїх даних.\n"
            "Використовуючи цього бота, ви погоджуєтесь з цією політикою."
        )
        sent = await message.answer(text, parse_mode="HTML")
        await state.update_data(last_info_message_id=sent.message_id)
        print(f"[INFO] /privacy: user {user_id} - policy sent")
    except Exception as e:
        data = await state.get_data()
        last_info_id = data.get('last_info_message_id')
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        sent = await message.answer("Сталася помилка при отриманні політики.")
        await state.update_data(last_info_message_id=sent.message_id)

@router.message(Command("disclaimer"))
async def disclaimer_handler(message: types.Message):
    user_id = message.from_user.id
    try:
        text = (
            "<b>Відмова від відповідальності</b>\n\n"
            "Бот є лише посередником між замовником і виконавцем.\n"
            "Адміністрація не несе відповідальності за якість виконання робіт, строки та інші зобов'язання, якщо інше не обумовлено окремо.\n"
            "Всі питання щодо виконання замовлення вирішуються напряму з менеджером."
        )
        await message.answer(text, parse_mode="HTML")
        print(f"[INFO] /disclaimer: user {user_id} - disclaimer sent")
    except Exception as e:
        print(f"[ERROR] /disclaimer: user {user_id} - {e}")
        await message.answer("Сталася помилка при отриманні відмови.")

@router.message(Command("myref"))
async def myref_handler(message: types.Message):
    user_id = message.from_user.id
    try:
        ref_link = f"https://t.me/{(await message.bot.me()).username}?start=ref{user_id}"
        referrals = get_referrals(user_id)
        text = (
            f"<b>Твоє реферальне посилання:</b>\n{ref_link}\n\n"
            f"Запрошено користувачів: <b>{len(referrals)}</b>"
        )
        await message.answer(text, parse_mode="HTML")
        print(f"[INFO] /myref: user {user_id} - ref link sent")
    except Exception as e:
        print(f"[ERROR] /myref: user {user_id} - {e}")
        await message.answer("Сталася помилка при отриманні реферального посилання.") 
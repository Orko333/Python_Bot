from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from datetime import datetime, timedelta
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from app.config import ORDER_TYPE_PRICES, Config
from app.db import add_order, get_promocode, use_promocode

router = Router()

class OrderStates(StatesGroup):
    waiting_for_topic = State()
    waiting_for_subject = State()
    waiting_for_deadline = State()
    waiting_for_volume = State()
    waiting_for_requirements = State()
    waiting_for_file = State()
    waiting_for_file_text = State()
    waiting_for_promocode = State()
    confirm = State()
    waiting_for_contact = State()

@router.callback_query(F.data.startswith("order_type:"))
async def order_type_callback(callback: types.CallbackQuery, state: FSMContext):
    code = callback.data.split(":", 1)[1]
    await state.update_data(order_type=code)
    await callback.message.edit_text("Введіть тему роботи:")
    await state.set_state(OrderStates.waiting_for_topic)
    await callback.answer()

@router.message(OrderStates.waiting_for_topic)
async def process_topic(message: types.Message, state: FSMContext):
    topic = message.text.strip()
    if not topic or len(topic) < 3:
        await message.answer("Тема занадто коротка. Введіть коректну тему (мінімум 3 символи):")
        return
    await state.update_data(topic=topic)
    await message.answer("Введіть предмет/дисципліну:")
    await state.set_state(OrderStates.waiting_for_subject)

@router.message(OrderStates.waiting_for_subject)
async def process_subject(message: types.Message, state: FSMContext):
    subject = message.text.strip()
    if not subject or len(subject) < 2:
        await message.answer("Введіть коректний предмет (мінімум 2 символи):")
        return
    await state.update_data(subject=subject)
    today = datetime.now().date()
    options = [
        (7, "Через 7 днів"),
        (14, "Через 14 днів"),
        (21, "Через 21 день"),
        (30, "Через 30 днів"),
        (45, "Через 45 днів"),
        (60, "Через 60 днів")
    ]
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"deadline:{(today + timedelta(days=days)).isoformat()}")]
        for days, label in options
    ]
    buttons.append([InlineKeyboardButton(text="Ввести вручну", callback_data="deadline:manual")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Оберіть дедлайн або введіть вручну:", reply_markup=keyboard)
    await state.set_state(OrderStates.waiting_for_deadline)

@router.callback_query(F.data.startswith("deadline:"), OrderStates.waiting_for_deadline)
async def process_deadline_callback(callback: types.CallbackQuery, state: FSMContext):
    deadline_str = callback.data.split(":", 1)[1]
    if deadline_str == "manual":
        await callback.message.edit_text("Введіть дедлайн у форматі YYYY-MM-DD (наприклад, 2024-07-15):")
        await state.set_state(OrderStates.waiting_for_deadline)
        await state.update_data(deadline_manual=True)
        await callback.answer()
        return
    await state.update_data(deadline=deadline_str, deadline_manual=False)
    await callback.message.edit_text(f"Дедлайн обрано: {datetime.strptime(deadline_str, '%Y-%m-%d').strftime('%d.%m.%Y')}")
    await callback.answer()
    await callback.message.answer("Введіть об'єм роботи (кількість сторінок/слайдів/робіт):")
    await state.set_state(OrderStates.waiting_for_volume)

@router.message(OrderStates.waiting_for_deadline)
async def process_deadline_manual(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("deadline_manual"):
        return  # ігноруємо, якщо не очікуємо ручний дедлайн
    try:
        deadline = datetime.strptime(message.text.strip(), "%Y-%m-%d").date()
        if deadline < datetime.now().date():
            raise ValueError
    except Exception:
        await message.answer("❗ Невірний формат дати або дата у минулому. Спробуйте ще раз у форматі YYYY-MM-DD.")
        return
    await state.update_data(deadline=deadline.isoformat(), deadline_manual=False)
    await message.answer(f"Дедлайн обрано: {deadline.strftime('%d.%m.%Y')}")
    await message.answer("Введіть об'єм роботи (кількість сторінок/слайдів/робіт):")
    await state.set_state(OrderStates.waiting_for_volume)

@router.message(OrderStates.waiting_for_volume)
async def process_volume(message: types.Message, state: FSMContext):
    volume = message.text.strip()
    try:
        v = int(volume)
        if v < 1 or v > 1000:
            raise ValueError
    except Exception:
        await message.answer("Введіть коректний об'єм (число від 1 до 1000):")
        return
    await state.update_data(volume=volume)
    await message.answer("Особливі вимоги? (або напишіть '-' якщо немає)")
    await state.set_state(OrderStates.waiting_for_requirements)

@router.message(OrderStates.waiting_for_requirements)
async def process_requirements(message: types.Message, state: FSMContext):
    requirements = message.text.strip()
    if len(requirements) > 500:
        await message.answer("Особливі вимоги занадто довгі (максимум 500 символів). Введіть коротше або напишіть '-':")
        return
    await state.update_data(requirements=requirements)
    await message.answer("Надішліть файл із завданням (або напишіть '-' якщо немає)")
    await state.set_state(OrderStates.waiting_for_file)

@router.message(OrderStates.waiting_for_file)
async def process_file(message: types.Message, state: FSMContext):
    if message.document:
        file_id = message.document.file_id
        await state.update_data(file_id=file_id)
        await message.answer("Файл отримано. Якщо хочете додати текстові методичні вказівки — напишіть їх зараз, або напишіть '-' якщо не потрібно.")
        await state.set_state(OrderStates.waiting_for_file_text)
        return
    elif message.text and message.text.strip() != "-":
        file_text = message.text.strip()
        await state.update_data(file_id=None, file_text=file_text)
        await message.answer("Текстові методичні вказівки збережено. Якщо у вас є промокод — введіть його зараз, або напишіть '-' якщо немає.")
        await state.set_state(OrderStates.waiting_for_promocode)
        return
    else:
        await state.update_data(file_id=None, file_text=None)
        await message.answer("Якщо у вас є промокод — введіть його зараз, або напишіть '-' якщо немає.")
        await state.set_state(OrderStates.waiting_for_promocode)

@router.message(OrderStates.waiting_for_file_text)
async def process_file_text(message: types.Message, state: FSMContext):
    if message.text and message.text.strip() != "-":
        file_text = message.text.strip()
        await state.update_data(file_text=file_text)
    else:
        await state.update_data(file_text=None)
    await message.answer("Якщо у вас є промокод — введіть його зараз, або напишіть '-' якщо немає.")
    await state.set_state(OrderStates.waiting_for_promocode)

@router.message(OrderStates.waiting_for_promocode)
async def process_promocode(message: types.Message, state: FSMContext):
    promocode = message.text.strip()
    data = await state.get_data()
    file_id = data.get('file_id')
    file_text = data.get('file_text')
    discount = 0
    discount_text = ""
    if promocode and promocode != "-":
        promo = get_promocode(promocode.upper())
        if promo:
            # promo: (code, discount_type, discount_value, usage_limit, used_count, created_at)
            if promo[3] is None or promo[4] < promo[3]:
                if promo[1] == "percent":
                    discount = int(data.get("price", 0)) * promo[2] // 100
                    discount_text = f"Промокод {promo[0]}: -{promo[2]}% (-{discount} грн)\n"
                elif promo[1] == "fixed":
                    discount = promo[2]
                    discount_text = f"Промокод {promo[0]}: -{discount} грн\n"
                use_promocode(message.from_user.id, promo[0])
            else:
                discount_text = f"Промокод {promo[0]} вже використано максимальну кількість разів."
        else:
            discount_text = "Промокод не знайдено або недійсний."
    # Підсумок
    order_type = data.get('order_type', 'other')
    price_info = ORDER_TYPE_PRICES.get(order_type, ORDER_TYPE_PRICES['other'])
    label = price_info['label']
    base = price_info['base']
    try:
        volume = int(data.get('volume', '1'))
        if volume < 1:
            volume = 1
    except Exception:
        volume = 1
    if 'per_page' in price_info:
        volume_price = price_info['per_page'] * volume
        volume_label = f"{price_info['per_page']} грн/сторінка"
    elif 'per_work' in price_info:
        volume_price = price_info['per_work'] * volume
        volume_label = f"{price_info['per_work']} грн/робота"
    else:
        volume_price = 0
        volume_label = "-"
    deadline = data.get('deadline', '')
    urgent_coef = 1.0
    urgent_label = ""
    try:
        days_left = (datetime.strptime(deadline, "%Y-%m-%d") - datetime.now()).days
        if days_left < 3:
            urgent_coef = 1.3
            urgent_label = "<b>+30% за терміновість (менше 3 днів)</b>"
        elif days_left < 7:
            urgent_coef = 1.15
            urgent_label = "+15% за терміновість (менше 7 днів)"
    except Exception:
        urgent_label = "(дедлайн не розпізнано, без надбавки)"
    requirements = data.get('requirements', '').strip()
    req_coef = 1.0
    req_label = ""
    if requirements and requirements != "-":
        req_coef = 1.2
        req_label = "+20% за особливі вимоги"
    price = (base + volume_price) * urgent_coef * req_coef
    price = int(round(price, -1))
    final_price = max(0, price - discount)
    summary = f"<b>Ваше замовлення:</b>\n"
    summary += f"Тип: {label}\n"
    summary += f"Тема: {data.get('topic')}\n"
    summary += f"Предмет: {data.get('subject')}\n"
    summary += f"Дедлайн: {deadline}\n"
    summary += f"Об'єм: {volume} ({volume_label})\n"
    summary += f"Вимоги: {requirements if requirements else '-'}\n"
    if file_id:
        summary += f"Файл: є\n"
    elif file_text:
        summary += f"Текстові методичні вказівки: {file_text}\n"
    else:
        summary += f"Файл: немає\n"
    summary += "\n<b>Розрахунок ціни:</b>\n"
    summary += f"Базова ціна: {base} грн\n"
    summary += f"За об'єм: {volume_price} грн\n"
    if urgent_label:
        summary += f"{urgent_label}\n"
    if req_label:
        summary += f"{req_label}\n"
    if discount_text:
        summary += discount_text + "\n"
    summary += f"<b>Орієнтовна ціна: {final_price} грн</b>\n"
    summary += "\nПідтвердити замовлення? (так/ні)"
    await state.update_data(price=final_price)
    await message.answer(summary, parse_mode="HTML")
    await state.set_state(OrderStates.confirm)

@router.message(OrderStates.confirm)
async def process_confirm(message: types.Message, state: FSMContext):
    if message.text.lower() in ["так", "yes", "+"]:
        # Попросити контакт
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Поділитись номером телефону", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await message.answer(
            "Для підтвердження замовлення, будь ласка, поділіться своїм номером телефону (це потрібно для зв'язку з менеджером):",
            reply_markup=kb
        )
        await state.set_state(OrderStates.waiting_for_contact)
    else:
        await message.answer("Замовлення скасовано.")
        await state.clear()

@router.message(OrderStates.waiting_for_contact)
async def process_contact(message: types.Message, state: FSMContext):
    contact = message.contact
    if not contact:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Поділитись номером телефону", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await message.answer("Будь ласка, натисніть кнопку нижче, щоб поділитись номером телефону:", reply_markup=kb)
        return
    user_data = await state.get_data()
    phone = str(contact.phone_number).strip()
    if not phone.startswith('+'):
        phone = '+' + phone
    file_id = user_data.get("file_id")
    file_text = user_data.get("file_text")
    user_data.update({
        "user_id": message.from_user.id,
        "first_name": message.from_user.first_name,
        "username": message.from_user.username,
        "phone_number": phone,
        "file_id": file_id,
        "file_text": file_text
    })
    order_type = user_data.get('order_type', 'other')
    price_info = ORDER_TYPE_PRICES.get(order_type, ORDER_TYPE_PRICES['other'])
    user_data["type_label"] = price_info["label"]
    user_data["price"] = user_data.get("price", "---")
    user_data["status"] = "нове"
    add_order(user_data)
    # --- Сповіщення адміну ---
    for admin_id in Config.ADMIN_IDS:
        try:
            msg = (
                f"<b>Нове замовлення!</b>\n"
                f"Тип: {user_data.get('type_label')}\n"
                f"Тема: {user_data.get('topic')}\n"
                f"Предмет: {user_data.get('subject')}\n"
                f"Дедлайн: {user_data.get('deadline')}\n"
                f"Об'єм: {user_data.get('volume')}\n"
                f"Вимоги: {user_data.get('requirements')}\n"
                f"Ціна: {user_data.get('price')} грн\n"
                f"user_id: {user_data.get('user_id')}\n"
                f"username: @{user_data.get('username')}\n"
                f"Телефон: {user_data.get('phone_number')}\n"
            )
            await message.bot.send_message(admin_id, msg, parse_mode="HTML")
            if file_id:
                await message.bot.send_document(admin_id, file_id, caption="Файл до замовлення")
            if file_text:
                await message.bot.send_message(admin_id, f"Текстові методичні вказівки: {file_text}")
        except Exception:
            pass
    await message.answer(
        "Дякуємо! Ваше замовлення прийнято. З вами зв'яжеться менеджер найближчим часом.",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.clear() 
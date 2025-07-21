from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from datetime import datetime, timedelta
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from app.config import ORDER_TYPE_PRICES, Config, ORDER_STATUSES, SPAM_LIMITS, MAX_FILES_PER_ORDER, ALLOWED_FILE_TYPES
from app.db import add_order, get_promocode, is_promocode_valid, use_promocode, update_order, get_order_by_id, check_spam_protection, add_referral_bonus, get_referrals
from app.utils.validation import validate_topic, validate_subject, validate_deadline, validate_volume, validate_requirements, validate_promocode
import json
import re

router = Router()

class OrderStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_topic = State()
    waiting_for_subject = State()
    waiting_for_deadline = State()
    waiting_for_volume = State()
    waiting_for_requirements = State()
    waiting_for_files = State()
    waiting_for_file_text = State()
    waiting_for_promocode = State()
    waiting_for_confirmation = State()
    editing_order = State()


def calculate_price(data: dict) -> tuple[float, float]:
    """Розраховує вартість замовлення на основі введених даних."""
    order_type = data.get("order_type")
    volume_str = data.get("volume", "0")
    deadline_str = data.get("deadline", "")
    promocode_data = data.get("promocode")

    if not order_type or order_type not in ORDER_TYPE_PRICES:
        return 0.0, 0.0

    price_info = ORDER_TYPE_PRICES[order_type]
    base_price = float(price_info.get("base", 0))
    total_price = base_price

    volume_match = re.search(r'\d+', volume_str)
    volume = int(volume_match.group(0)) if volume_match else 0

    if "per_page" in price_info:
        total_price += volume * float(price_info["per_page"])
    elif "per_work" in price_info:
        total_price += volume * float(price_info["per_work"])

    try:
        # Спроба розпарсити різні формати дати
        parsed_date = None
        for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"]:
             try:
                 parsed_date = datetime.strptime(deadline_str, fmt)
                 break
             except ValueError:
                 continue
        
        if parsed_date:
            days_to_deadline = (parsed_date - datetime.now()).days
            if days_to_deadline < 3:
                total_price *= 1.5
            elif days_to_deadline < 7:
                total_price *= 1.25
    except TypeError:
        pass

    discount = 0.0
    if promocode_data:
        promo_type = promocode_data[2]
        promo_value = float(promocode_data[3])
        if promo_type == 'percent':
            discount = total_price * (promo_value / 100)
        elif promo_type == 'fixed':
            discount = promo_value

    final_price = total_price - discount
    return max(0, final_price), discount


def get_back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Назад"), KeyboardButton(text="❌ Скасувати")]],
        resize_keyboard=True
    )

def get_main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Мій кабінет"), KeyboardButton(text="📝 Нове замовлення")]
        ],
        resize_keyboard=True
    )

def get_progress_bar(current_step, total_steps):
    steps = {
        1: ("📝", "Тип роботи"),
        2: ("📖", "Тема"),
        3: ("📚", "Предмет"),
        4: ("⏰", "Термін"),
        5: ("📊", "Обсяг"),
        6: ("📋", "Вимоги"),
        7: ("📎", "Файли"),
        8: ("🎫", "Промокод")
    }
    
    progress_lines = []
    for step_num in range(1, total_steps + 1):
        emoji, text = steps.get(step_num)
        if step_num == current_step:
            progress_lines.append(f"▶️ <b>{emoji} {text}</b> ◀️")
        elif step_num < current_step:
            progress_lines.append(f"✅ {emoji} {text}")
        else:
            progress_lines.append(f"◽️ {emoji} {text}")
    
    progress_display = "\n".join(progress_lines)
    header = "<b>📝 Створення нового замовлення</b>\n"
    return f"{header}\n{progress_display}"

@router.message(Command("order"))
@router.message(F.text == "📝 Нове замовлення")
async def order_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        if not check_spam_protection(message.from_user.id, 'order_creation', 
                                    SPAM_LIMITS['order_creation']['limit'], 
                                    SPAM_LIMITS['order_creation']['window']):
            data = await state.get_data()
            last_info_id = data.get('last_info_message_id')
            if last_info_id:
                try:
                    await message.bot.delete_message(message.chat.id, last_info_id)
                except: pass
            sent = await message.answer("⚠️ Занадто багато замовлень. Спробуйте пізніше.")
            await state.update_data(last_info_message_id=sent.message_id)
            print(f"[ERROR] /order: user {user_id} - spam protection triggered")
            return
        
        await state.clear()
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=info['label'], callback_data=f"order_type:{code}")]
                for code, info in ORDER_TYPE_PRICES.items()
            ]
        )
        sent = await message.answer(
            f"{get_progress_bar(1, 8)}\n\n"
            "Оберіть тип роботи:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await state.update_data(last_info_message_id=sent.message_id)
        print(f"[INFO] /order: user {user_id} - order menu sent")
    except Exception as e:
        data = await state.get_data()
        last_info_id = data.get('last_info_message_id')
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        sent = await message.answer("Сталася помилка при створенні замовлення.")
        await state.update_data(last_info_message_id=sent.message_id)

@router.callback_query(lambda c: c.data and c.data.startswith('order_type:'))
async def order_type_callback(callback: types.CallbackQuery, state: FSMContext):
    order_type = callback.data.split(':')[1]
    await state.update_data(order_type=order_type)
    
    keyboard = get_back_keyboard()
    await callback.message.delete() # Видаляємо повідомлення з кнопками
    prompt_message = await callback.message.answer(
        f"{get_progress_bar(2, 8)}\n\n"
        "Введіть тему роботи:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.update_data(last_bot_message_id=prompt_message.message_id)
    await state.set_state(OrderStates.waiting_for_topic)
    
    # Розраховуємо та зберігаємо ціну
    price, discount = calculate_price(await state.get_data())
    await state.update_data(price=price, discount=discount)
    
    await callback.answer()

@router.message(OrderStates.waiting_for_topic)
async def process_topic(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_bot_message_id = data.get('last_bot_message_id')
    last_info_id = data.get('last_info_message_id')

    if message.text == "🔙 Назад":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=info['label'], callback_data=f"order_type:{code}")]
                for code, info in ORDER_TYPE_PRICES.items()
            ]
        )
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        sent = await message.answer("Оберіть тип роботи:", reply_markup=keyboard)
        await state.update_data(last_info_message_id=sent.message_id)
        await state.set_state(OrderStates.waiting_for_type)
        return
    
    if message.text == "❌ Скасувати":
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        sent = await message.answer("Створення замовлення скасовано.", reply_markup=get_main_menu_keyboard())
        await state.update_data(last_info_message_id=sent.message_id)
        await state.clear()
        return
    
    is_valid, error_message = validate_topic(message.text)
    if not is_valid:
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        try:
            await message.delete()
        except: pass
        sent = await message.answer(f"⚠️ {error_message}")
        await state.update_data(last_info_message_id=sent.message_id)
        return
    
    if last_bot_message_id:
        try:
            await message.bot.delete_message(message.chat.id, last_bot_message_id)
        except: pass
    try:
        await message.delete()
    except: pass
    
    await state.update_data(topic=message.text)
    keyboard = get_back_keyboard()
    prompt_message = await message.answer(
        f"{get_progress_bar(3, 8)}\n\n"
        "Введіть предмет:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.update_data(last_bot_message_id=prompt_message.message_id)
    await state.set_state(OrderStates.waiting_for_subject)

@router.message(OrderStates.waiting_for_subject)
async def process_subject(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_bot_message_id = data.get('last_bot_message_id')
    last_info_id = data.get('last_info_message_id')

    if message.text == "🔙 Назад":
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await message.bot.delete_message(message.chat.id, last_bot_message_id)
            except: pass
        try:
            await message.delete()
        except: pass
        await state.set_state(OrderStates.waiting_for_topic)
        keyboard = get_back_keyboard()
        sent = await message.answer("Введіть тему роботи:", reply_markup=keyboard)
        await state.update_data(last_bot_message_id=sent.message_id)
        return
    
    if message.text == "❌ Скасувати":
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await message.bot.delete_message(message.chat.id, last_bot_message_id)
            except: pass
        try:
            await message.delete()
        except: pass
        sent = await message.answer("Створення замовлення скасовано.", reply_markup=get_main_menu_keyboard())
        await state.update_data(last_info_message_id=sent.message_id)
        await state.clear()
        return
    
    is_valid, error_message = validate_subject(message.text)
    if not is_valid:
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        try:
            await message.delete()
        except: pass
        sent = await message.answer(f"⚠️ {error_message}")
        await state.update_data(last_info_message_id=sent.message_id)
        return
        
    if last_bot_message_id:
        try:
            await message.bot.delete_message(message.chat.id, last_bot_message_id)
        except: pass
    try:
        await message.delete()
    except: pass

    await state.update_data(subject=message.text)
    keyboard = get_back_keyboard()
    prompt_message = await message.answer(
        f"{get_progress_bar(4, 8)}\n\n"
        "Введіть термін виконання (наприклад: 7 днів, 2 тижні):",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.update_data(last_bot_message_id=prompt_message.message_id)
    await state.set_state(OrderStates.waiting_for_deadline)

@router.message(OrderStates.waiting_for_deadline)
async def process_deadline(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_bot_message_id = data.get('last_bot_message_id')
    last_info_id = data.get('last_info_message_id')

    if message.text == "🔙 Назад":
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await message.bot.delete_message(message.chat.id, last_bot_message_id)
            except: pass
        try:
            await message.delete()
        except: pass
        await state.set_state(OrderStates.waiting_for_subject)
        keyboard = get_back_keyboard()
        sent = await message.answer("Введіть предмет:", reply_markup=keyboard)
        await state.update_data(last_bot_message_id=sent.message_id)
        return
    
    if message.text == "❌ Скасувати":
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await message.bot.delete_message(message.chat.id, last_bot_message_id)
            except: pass
        try:
            await message.delete()
        except: pass
        sent = await message.answer("Створення замовлення скасовано.", reply_markup=get_main_menu_keyboard())
        await state.update_data(last_info_message_id=sent.message_id)
        await state.clear()
        return
    
    is_valid, error_message = validate_deadline(message.text)
    if not is_valid:
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        try:
            await message.delete()
        except: pass
        sent = await message.answer(f"⚠️ {error_message}")
        await state.update_data(last_info_message_id=sent.message_id)
        return

    if last_bot_message_id:
        try:
            await message.bot.delete_message(message.chat.id, last_bot_message_id)
        except: pass
    try:
        await message.delete()
    except: pass
    
    await state.update_data(deadline=message.text)

    # Розраховуємо та зберігаємо ціну
    price, discount = calculate_price(await state.get_data())
    await state.update_data(price=price, discount=discount)

    keyboard = get_back_keyboard()
    prompt_message = await message.answer(
        f"{get_progress_bar(5, 8)}\n\n"
        "Введіть обсяг роботи (кількість сторінок або робіт):",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.update_data(last_bot_message_id=prompt_message.message_id)
    await state.set_state(OrderStates.waiting_for_volume)

@router.message(OrderStates.waiting_for_volume)
async def process_volume(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_bot_message_id = data.get('last_bot_message_id')
    last_info_id = data.get('last_info_message_id')

    if message.text == "🔙 Назад":
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await message.bot.delete_message(message.chat.id, last_bot_message_id)
            except: pass
        try:
            await message.delete()
        except: pass
        await state.set_state(OrderStates.waiting_for_deadline)
        keyboard = get_back_keyboard()
        sent = await message.answer("Введіть термін виконання:", reply_markup=keyboard)
        await state.update_data(last_bot_message_id=sent.message_id)
        return
    
    if message.text == "❌ Скасувати":
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await message.bot.delete_message(message.chat.id, last_bot_message_id)
            except: pass
        try:
            await message.delete()
        except: pass
        sent = await message.answer("Створення замовлення скасовано.", reply_markup=get_main_menu_keyboard())
        await state.update_data(last_info_message_id=sent.message_id)
        await state.clear()
        return
    
    is_valid, error_message = validate_volume(message.text)
    if not is_valid:
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        try:
            await message.delete()
        except: pass
        sent = await message.answer(f"⚠️ {error_message}")
        await state.update_data(last_info_message_id=sent.message_id)
        return

    if last_bot_message_id:
        try:
            await message.bot.delete_message(message.chat.id, last_bot_message_id)
        except: pass
    try:
        await message.delete()
    except: pass
    
    await state.update_data(volume=message.text)
    
    # Розраховуємо та зберігаємо ціну
    price, discount = calculate_price(await state.get_data())
    await state.update_data(price=price, discount=discount)
    
    keyboard = get_back_keyboard()
    prompt_message = await message.answer(
        f"{get_progress_bar(6, 8)}\n\n"
        "Введіть вимоги до роботи:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.update_data(last_bot_message_id=prompt_message.message_id)
    await state.set_state(OrderStates.waiting_for_requirements)

@router.message(OrderStates.waiting_for_requirements)
async def process_requirements(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_bot_message_id = data.get('last_bot_message_id')
    last_info_id = data.get('last_info_message_id')

    if message.text == "🔙 Назад":
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await message.bot.delete_message(message.chat.id, last_bot_message_id)
            except: pass
        try:
            await message.delete()
        except: pass
        await state.set_state(OrderStates.waiting_for_volume)
        keyboard = get_back_keyboard()
        sent = await message.answer("Введіть обсяг роботи:", reply_markup=keyboard)
        await state.update_data(last_bot_message_id=sent.message_id)
        return
    
    if message.text == "❌ Скасувати":
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await message.bot.delete_message(message.chat.id, last_bot_message_id)
            except: pass
        try:
            await message.delete()
        except: pass
        sent = await message.answer("Створення замовлення скасовано.", reply_markup=get_main_menu_keyboard())
        await state.update_data(last_info_message_id=sent.message_id)
        await state.clear()
        return
    
    is_valid, error_message = validate_requirements(message.text)
    if not is_valid:
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        try:
            await message.delete()
        except: pass
        sent = await message.answer(f"⚠️ {error_message}")
        await state.update_data(last_info_message_id=sent.message_id)
        return

    if last_bot_message_id:
        try:
            await message.bot.delete_message(message.chat.id, last_bot_message_id)
        except: pass
    try:
        await message.delete()
    except: pass
    
    await state.update_data(requirements=message.text)
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📎 Додати файли"), KeyboardButton(text="⏭️ Пропустити")],
            [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="❌ Скасувати")]
        ],
        resize_keyboard=True
    )
    prompt_message = await message.answer(
        f"{get_progress_bar(7, 8)}\n\n"
        "Бажаєте додати файли до замовлення?",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.update_data(last_bot_message_id=prompt_message.message_id)
    await state.set_state(OrderStates.waiting_for_files)

@router.message(OrderStates.waiting_for_files)
async def process_files_choice(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_bot_message_id = data.get('last_bot_message_id')
    last_info_id = data.get('last_info_message_id')

    if message.text == "🔙 Назад":
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await message.bot.delete_message(message.chat.id, last_bot_message_id)
            except: pass
        try:
            await message.delete()
        except: pass
        await state.set_state(OrderStates.waiting_for_requirements)
        keyboard = get_back_keyboard()
        sent = await message.answer("Введіть вимоги до роботи:", reply_markup=keyboard)
        await state.update_data(last_bot_message_id=sent.message_id)
        return
    
    if message.text == "❌ Скасувати":
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await message.bot.delete_message(message.chat.id, last_bot_message_id)
            except: pass
        try:
            await message.delete()
        except: pass
        sent = await message.answer("Створення замовлення скасовано.", reply_markup=get_main_menu_keyboard())
        await state.update_data(last_info_message_id=sent.message_id)
        await state.clear()
        return
    
    if last_bot_message_id:
        try:
            await message.bot.delete_message(message.chat.id, last_bot_message_id)
        except: pass
    try:
        await message.delete()
    except: pass

    if message.text == "📎 Додати файли":
        await state.update_data(files=[])
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Готово"), KeyboardButton(text="🔙 Назад")],
                [KeyboardButton(text="❌ Скасувати")]
            ],
            resize_keyboard=True
        )
        prompt_message = await message.answer(
            "Надішліть файли (до 10 файлів, максимум 20MB кожен).\n"
            "Підтримуються: PDF, DOC, DOCX, TXT, JPG, PNG, GIF",
            reply_markup=keyboard
        )
        await state.update_data(last_bot_message_id=prompt_message.message_id)
        await state.set_state(OrderStates.waiting_for_file_text)
    elif message.text == "⏭️ Пропустити":
        await state.update_data(files=[])
        await go_to_promocode_step(message, state)


@router.message(OrderStates.waiting_for_file_text, F.document | F.photo | F.video)
async def process_file_upload(message: types.Message, state: FSMContext):
    data = await state.get_data()
    files = data.get('files', [])
    
    try:
        await message.delete()
    except:
        pass

    if len(files) >= MAX_FILES_PER_ORDER:
        sent = await message.answer(f"⚠️ Максимальна кількість файлів: {MAX_FILES_PER_ORDER}")
        # Store sent message id to delete it later
        temp_messages = data.get('temp_messages', [])
        temp_messages.append(sent.message_id)
        await state.update_data(temp_messages=temp_messages)
        return
    
    file_id = None
    file_size = None
    file_type = None
    if message.document:
        file_id = message.document.file_id
        file_size = message.document.file_size
        file_type = message.document.mime_type
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_size = getattr(message.photo[-1], 'file_size', None)
        file_type = "image/jpeg"
    elif message.video:
        file_id = message.video.file_id
        file_size = message.video.file_size
        file_type = message.video.mime_type
    
    if file_size is not None and file_size > Config.MAX_FILE_SIZE:
        sent = await message.answer("⚠️ Файл занадто великий. Максимальний розмір: 20MB")
        temp_messages = data.get('temp_messages', [])
        temp_messages.append(sent.message_id)
        await state.update_data(temp_messages=temp_messages)
        return
    
    if file_type not in ALLOWED_FILE_TYPES:
        sent = await message.answer("⚠️ Непідтримуваний тип файлу")
        temp_messages = data.get('temp_messages', [])
        temp_messages.append(sent.message_id)
        await state.update_data(temp_messages=temp_messages)
        return
    
    files.append(file_id)
    await state.update_data(files=files)
    
    sent = await message.answer(f"✅ Файл додано! ({len(files)}/{MAX_FILES_PER_ORDER})")
    temp_messages = data.get('temp_messages', [])
    temp_messages.append(sent.message_id)
    await state.update_data(temp_messages=temp_messages)

@router.message(OrderStates.waiting_for_file_text)
async def process_file_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_bot_message_id = data.get('last_bot_message_id')
    last_info_id = data.get('last_info_message_id')
    chat_id = message.chat.id
    bot = message.bot

    # Delete temp messages (e.g., "File added", "File too large")
    temp_messages = data.get('temp_messages', [])
    for msg_id in temp_messages:
        try:
            await bot.delete_message(chat_id, msg_id)
        except:
            pass
    await state.update_data(temp_messages=[])

    try:
        await message.delete()
    except:
        pass

    if message.text == "✅ Готово":
        if last_bot_message_id:
            try:
                await bot.delete_message(chat_id, last_bot_message_id)
            except:
                pass
        if len(data.get('files', [])) == 0:
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="✅ Продовжити без файлів")],
                    [KeyboardButton(text="📎 Додати файли"), KeyboardButton(text="🔙 Назад")],
                    [KeyboardButton(text="❌ Скасувати")]
                ],
                resize_keyboard=True
            )
            if last_info_id:
                try:
                    await bot.delete_message(chat_id, last_info_id)
                except: pass
            sent = await bot.send_message(
                chat_id,
                "Ви не додали жодного файлу. Продовжити без файлів?",
                reply_markup=keyboard
            )
            await state.update_data(last_info_message_id=sent.message_id)
            return
        await go_to_promocode_step(message, state)
    elif message.text == "✅ Продовжити без файлів":
        if last_bot_message_id:
            try:
                await bot.delete_message(chat_id, last_bot_message_id)
            except:
                pass
        await go_to_promocode_step(message, state)
    elif message.text == "🔙 Назад":
        if last_info_id:
            try:
                await bot.delete_message(chat_id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await bot.delete_message(chat_id, last_bot_message_id)
            except: pass
        await state.set_state(OrderStates.waiting_for_requirements)
        keyboard = get_back_keyboard()
        sent = await bot.send_message(chat_id, "Введіть вимоги до роботи:", reply_markup=keyboard)
        await state.update_data(last_bot_message_id=sent.message_id)
    elif message.text == "❌ Скасувати":
        if last_info_id:
            try:
                await bot.delete_message(chat_id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await bot.delete_message(chat_id, last_bot_message_id)
            except: pass
        sent = await bot.send_message(chat_id, "Створення замовлення скасовано.", reply_markup=get_main_menu_keyboard())
        await state.update_data(last_info_message_id=sent.message_id)
        await state.clear()
    else:
        if last_info_id:
            try:
                await bot.delete_message(chat_id, last_info_id)
            except: pass
        sent = await bot.send_message(chat_id, "Надішліть файл або натисніть 'Готово'")
        await state.update_data(last_info_message_id=sent.message_id)


async def go_to_promocode_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_bot_message_id = data.get('last_bot_message_id')

    if last_bot_message_id:
        try:
            await message.bot.delete_message(message.chat.id, last_bot_message_id)
        except: pass
    try:
        await message.delete()
    except: pass

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭️ Без промокоду")],
            [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="❌ Скасувати")]
        ],
        resize_keyboard=True
    )
    prompt_message = await message.answer(
        f"{get_progress_bar(8, 8)}\n\n"
        "Введіть промокод (якщо є):",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.update_data(last_bot_message_id=prompt_message.message_id)
    await state.set_state(OrderStates.waiting_for_promocode)


@router.message(OrderStates.waiting_for_promocode)
async def process_promocode_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_bot_message_id = data.get('last_bot_message_id')
    last_info_id = data.get('last_info_message_id')
    bot = message.bot
    chat_id = message.chat.id

    try:
        await message.delete()
    except: pass

    if message.text == "🔙 Назад":
        if last_info_id:
            try:
                await bot.delete_message(chat_id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await bot.delete_message(chat_id, last_bot_message_id)
            except: pass
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📎 Додати файли"), KeyboardButton(text="⏭️ Пропустити")],
                [KeyboardButton(text="🔙 Назад"), KeyboardButton(text="❌ Скасувати")]
            ],
            resize_keyboard=True
        )
        prompt_message = await bot.send_message(chat_id,
            f"{get_progress_bar(7, 8)}\n\n"
            "Бажаєте додати файли до замовлення?",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await state.update_data(last_info_message_id=prompt_message.message_id)
        await state.set_state(OrderStates.waiting_for_files)
        return
    
    if message.text == "❌ Скасувати":
        if last_info_id:
            try:
                await bot.delete_message(chat_id, last_info_id)
            except: pass
        if last_bot_message_id:
            try:
                await bot.delete_message(chat_id, last_bot_message_id)
            except: pass
        sent = await bot.send_message(chat_id, "Створення замовлення скасовано.", reply_markup=get_main_menu_keyboard())
        await state.update_data(last_info_message_id=sent.message_id)
        await state.clear()
        return
    
    if message.text == "⏭️ Без промокоду":
        await state.update_data(promocode=None, discount=0)
        # Оновлюємо ціну без промокоду
        data = await state.get_data()
        price, _ = calculate_price(data)
        await state.update_data(price=price)
        await show_order_summary(message, state)
        return
    
    promocode = message.text.strip().upper()
    is_valid, error_message = validate_promocode(promocode)
    if not is_valid:
        if last_info_id:
            try:
                await bot.delete_message(chat_id, last_info_id)
            except: pass
        prompt_message = await bot.send_message(chat_id, f"⚠️ {error_message}")
        await state.update_data(last_info_message_id=prompt_message.message_id)
        return

    promo_data = get_promocode(promocode)
    
    if not promo_data or not is_promocode_valid(promo_data[0]):
        if last_bot_message_id:
            try:
                await bot.delete_message(chat_id, last_bot_message_id)
            except: pass
        if last_info_id:
            try:
                await bot.delete_message(chat_id, last_info_id)
            except: pass
        prompt_message = await bot.send_message(chat_id, "⚠️ Невірний або недійсний промокод. Спробуйте ще раз або натисніть 'Без промокоду'")
        await state.update_data(last_bot_message_id=prompt_message.message_id)
        return
    
    await state.update_data(promocode=promo_data)
    
    # Розраховуємо ціну зі знижкою
    data = await state.get_data()
    price, discount = calculate_price(data)
    await state.update_data(price=price, discount=discount)

    await show_order_summary(message, state)


async def get_summary_text_and_keyboard(state: FSMContext):
    """Готує текст та клавіатуру для підсумку замовлення."""
    data = await state.get_data()
    summary = f"""
📋 <b>Підсумок замовлення:</b>

📝 <b>Тип роботи:</b> {ORDER_TYPE_PRICES.get(data.get('order_type'), {}).get('label', 'Не вказано')}
📖 <b>Тема:</b> {data.get('topic', 'Не вказано')}
📚 <b>Предмет:</b> {data.get('subject', 'Не вказано')}
⏰ <b>Термін:</b> {data.get('deadline', 'Не вказано')}
📊 <b>Обсяг:</b> {data.get('volume', 'Не вказано')}
📋 <b>Вимоги:</b> {data.get('requirements', 'Не вказано')}
📎 <b>Файли:</b> {len(data.get('files', []))} шт.

💰 <b>Вартість:</b> {data.get('price', 0) + data.get('discount', 0):.2f} грн
🎫 <b>Знижка:</b> {data.get('discount', 0):.2f} грн
💳 <b>До сплати:</b> {data.get('price', 0):.2f} грн
"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Підтвердити", callback_data="confirm_order")],
            [InlineKeyboardButton(text="✏️ Редагувати", callback_data="edit_order")],
            [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_order")]
        ]
    )
    
    text_with_action = f"{summary}\n\nОберіть дію:"
    return text_with_action, keyboard

async def show_order_summary(message: types.Message, state: FSMContext, should_edit: bool = False):
    data = await state.get_data()
    last_info_id = data.get('last_info_message_id')
    last_bot_message_id = data.get('last_bot_message_id')
    
    # Delete previous messages
    if last_info_id and (not hasattr(message, 'message_id') or last_info_id != message.message_id):
        try:
            await message.bot.delete_message(message.chat.id, last_info_id)
        except: pass
    if last_bot_message_id:
        try:
            await message.bot.delete_message(message.chat.id, last_bot_message_id)
        except: pass

    if not should_edit:
        try:
            await message.delete()
        except: pass

    text_with_action, keyboard = await get_summary_text_and_keyboard(state)
    
    if should_edit:
        try:
            await message.edit_text(
                text_with_action, 
                parse_mode="HTML", 
                reply_markup=keyboard
            )
        except Exception: # If editing fails (e.g., message too old), send a new one
            sent = await message.answer(
                text_with_action,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await state.update_data(last_info_message_id=sent.message_id)
    else:
        sent = await message.answer(
            text_with_action,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await state.update_data(last_info_message_id=sent.message_id)

    await state.set_state(OrderStates.waiting_for_confirmation)

@router.callback_query(OrderStates.waiting_for_confirmation, lambda c: c.data == "confirm_order")
async def confirm_order_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    order_id = add_order(
        user_id=callback.from_user.id,
        first_name=callback.from_user.first_name,
        username=callback.from_user.username,
        phone_number="",
        type_label=ORDER_TYPE_PRICES[data['order_type']]['label'],
        order_type=data['order_type'],
        topic=data['topic'],
        subject=data['subject'],
        deadline=data['deadline'],
        volume=data['volume'],
        requirements=data['requirements'],
        price=data['price'],
        files=data.get('files', [])
    )
    
    if data.get('promocode'):
        use_promocode(data['promocode'][0], callback.from_user.id, order_id, data['discount'])
    
    referrals = get_referrals(callback.from_user.id)
    if referrals and data['price'] >= Config.REFERRAL_MIN_ORDER_AMOUNT:
        for ref in referrals:
            bonus_amount = data['price'] * Config.REFERRAL_BONUS_PERCENT // 100
            add_referral_bonus(ref[0], callback.from_user.id, order_id, bonus_amount)
    
    await callback.message.answer(
        f"✅ <b>Замовлення успішно створено!</b>\n\n"
        f"Наш менеджер зв'яжеться з вами найближчим часом.\n"
        f"Для перегляду замовлення використайте /cabinet",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )
    await state.clear()
    await callback.answer()

@router.callback_query(OrderStates.waiting_for_confirmation, lambda c: c.data == "edit_order")
async def edit_order_callback(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Тема", callback_data="edit_topic")],
            [InlineKeyboardButton(text="📚 Предмет", callback_data="edit_subject")],
            [InlineKeyboardButton(text="⏰ Термін", callback_data="edit_deadline")],
            [InlineKeyboardButton(text="📊 Обсяг", callback_data="edit_volume")],
            [InlineKeyboardButton(text="📋 Вимоги", callback_data="edit_requirements")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_summary")]
        ]
    )
    
    await callback.message.edit_text(
        "✏️ Що бажаєте редагувати?",
        reply_markup=keyboard
    )
    await state.set_state(OrderStates.editing_order)
    await callback.answer()

@router.callback_query(OrderStates.editing_order, lambda c: c.data == "back_to_summary")
async def back_to_summary_callback(callback: types.CallbackQuery, state: FSMContext):
    await show_order_summary(callback.message, state, should_edit=True)
    await callback.answer()

@router.callback_query(OrderStates.waiting_for_confirmation, lambda c: c.data == "cancel_order")
async def cancel_order_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Створення замовлення скасовано.")
    await callback.message.answer("Оберіть наступну дію:", reply_markup=get_main_menu_keyboard())
    await callback.answer()

@router.callback_query(OrderStates.editing_order, lambda c: c.data.startswith("edit_"))
async def edit_field_callback(callback: types.CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[1]
    field_names = {
        "topic": "тему",
        "subject": "предмет",
        "deadline": "термін",
        "volume": "обсяг",
        "requirements": "вимоги"
    }
    await state.update_data(editing_field=field)
    keyboard = get_back_keyboard()
    
    # Delete the summary message before asking for new input
    await callback.message.delete()

    prompt_message = await callback.message.answer(f"Введіть новий {field_names[field]}:", reply_markup=keyboard)
    await state.update_data(last_edit_message_id=prompt_message.message_id)
    await callback.answer()

@router.message(OrderStates.editing_order)
async def process_edit_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    editing_field = data.get('editing_field')
    last_edit_message_id = data.get('last_edit_message_id')
    last_info_id = data.get('last_info_message_id') # The original summary message
    bot = message.bot
    chat_id = message.chat.id

    if last_edit_message_id:
        try:
            await bot.delete_message(chat_id, last_edit_message_id)
        except: pass
    
    user_text = message.text
    try:
        await message.delete()
    except:
        pass

    if user_text == "🔙 Назад":
        # Since we deleted the original summary, we must send a new one
        await show_order_summary(message, state) # `message` is deleted but obj can be used for context
        return
    
    if user_text == "❌ Скасувати":
        await state.clear()
        await bot.send_message(chat_id, "Редагування скасовано.", reply_markup=get_main_menu_keyboard())
        return
    
    # Validator function mapping
    validation_functions = {
        "topic": validate_topic,
        "subject": validate_subject,
        "deadline": validate_deadline,
        "volume": validate_volume,
        "requirements": validate_requirements
    }

    validator = validation_functions.get(editing_field)
    if validator:
        is_valid, error_message = validator(user_text)
        if not is_valid:
            # Delete previous error message if any
            if data.get('edit_error_id'):
                try: await bot.delete_message(chat_id, data.get('edit_error_id'))
                except: pass

            sent_error = await bot.send_message(chat_id, f"⚠️ {error_message}")
            
            # Resend prompt
            field_names = {
                "topic": "тему", "subject": "предмет", "deadline": "термін",
                "volume": "обсяг", "requirements": "вимоги"
            }
            keyboard = get_back_keyboard()
            prompt = await bot.send_message(chat_id, f"Введіть новий {field_names.get(editing_field, 'параметр')}:", reply_markup=keyboard)
            
            await state.update_data(last_edit_message_id=prompt.message_id, edit_error_id=sent_error.message_id)
            return

    await state.update_data(**{editing_field: user_text})
    
    # Перераховуємо ціну після редагування
    new_data = await state.get_data()
    price, discount = calculate_price(new_data)
    await state.update_data(price=price, discount=discount)

    await state.update_data(editing_field=None)
    # Since the original summary was deleted, send a new one.
    # The `message` object is already deleted, but we can still use it for context (bot, chat)
    await show_order_summary(message, state, should_edit=False)
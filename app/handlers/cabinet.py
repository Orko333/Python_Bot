import json
import os
from aiogram import types, Router
from aiogram.filters import Command
from aiogram import Bot
from app.config import Config
from app.handlers.feedback import request_feedback
from collections import Counter
from datetime import datetime, timedelta
from app.db import get_orders, get_order_by_num, find_orders, update_order_status, add_promocode, get_promocode, get_promocode_usages
import re
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()
ORDERS_FILE = "orders.json"

# Функція для збереження замовлення
def save_order(order: dict):
    orders = []
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            try:
                orders = json.load(f)
            except Exception:
                orders = []
    orders.append(order)
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

# Функція для отримання замовлень користувача
def get_user_orders(user_id: int):
    if not os.path.exists(ORDERS_FILE):
        return []
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        try:
            orders = json.load(f)
        except Exception:
            return []
    return [o for o in orders if o.get("user_id") == user_id]

@router.message(Command("cabinet"))
async def cabinet_handler(message: types.Message):
    user_id = message.from_user.id
    orders = get_orders(user_id=user_id)
    if not orders:
        await message.answer("У вас ще немає замовлень.")
        return
    text = "<b>Ваші замовлення:</b>\n"
    for i, o in enumerate(orders, 1):
        text += (
            f"\n<b>{i} (ID:{o[0]})</b> {o[6]}\n"  # type_label + номер
            f"Тема: {o[8]}\n"         # topic
            f"Дедлайн: {o[10]}\n"      # deadline
            f"Ціна: {o[13]} грн\n"     # price
            f"Статус: {o[14]}\n"       # status
        )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("setstatus"))
async def setstatus_handler(message: types.Message, bot: Bot):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.answer("⛔ Тільки адміністратор може змінювати статуси.")
        return
    args = message.text.split()
    if len(args) != 3:
        await message.answer("Використання: /setstatus <номер> <статус>\nНаприклад: /setstatus 2 done")
        return
    try:
        order_num = int(args[1])
        new_status = args[2]
    except Exception:
        await message.answer("Невірний формат команди.")
        return
    ok, order_id = update_order_status(order_num, new_status)
    if not ok:
        await message.answer("Замовлення з таким номером не знайдено.")
        return
    o = get_order_by_num(order_num)
    user_id = o[2]
    try:
        await bot.send_message(user_id, f"Статус вашого замовлення №{order_num} змінено на: <b>{new_status}</b>", parse_mode="HTML")
        if new_status in ["готове", "оплачено", "done", "paid"]:
            await request_feedback(user_id, bot)
    except Exception:
        await message.answer("Не вдалося надіслати сповіщення користувачу.")
    await message.answer(f"Статус замовлення №{order_num} змінено на {new_status}.")

@router.message(Command("orders"))
async def admin_orders(message: types.Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.answer("⛔ Тільки адміністратор може переглядати всі замовлення.")
        return
    args = message.text.split()
    status_filter = args[1] if len(args) > 1 else None
    orders = get_orders(status=status_filter)
    if not orders:
        await message.answer("Замовлень ще немає.")
        return
    # Фільтруємо завершені замовлення
    completed_statuses = {"готово", "оплачено", "done", "paid", "завершено"}
    active_orders = [o for o in orders if str(o[14]).lower() not in completed_statuses]
    # Сортуємо за дедлайном (найближчі зверху)
    def parse_deadline(o):
        try:
            return datetime.strptime(o[10], "%Y-%m-%d")
        except Exception:
            return datetime.max
    active_orders.sort(key=parse_deadline)
    text = f"<b>Актуальні замовлення (найближчі дедлайни зверху):</b>\n"
    for i, o in enumerate(active_orders, 1):
        text += (
            f"\n<b>{i} (ID:{o[0]})</b> {o[6]}\n"
            f"Тема: {o[8]}\n"
            f"Дедлайн: {o[10]}\n"
            f"Ціна: {o[13]} грн\n"
            f"Статус: {o[14]}\n"
            f"user_id: {o[1]}\n"
        )
    if not active_orders:
        text += "\nНемає активних замовлень."
    await message.answer(text, parse_mode="HTML")

@router.message(Command(re.compile(r"order_(\d+)")))
async def admin_order_detail_underscore(message: types.Message, command: CommandObject):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.answer("⛔ Тільки адміністратор може переглядати деталі замовлення.")
        return
    try:
        order_num = int(command.command.split('_')[1])
    except Exception:
        await message.answer("Невірний формат команди. Приклад: /order_5")
        return
    o = get_order_by_num(order_num)
    if not o:
        await message.answer("Замовлення з таким номером не знайдено.")
        return
    text = (
        f"<b>Деталі замовлення №{order_num}:</b>\n"
        f"Тип: {o[6]}\n"
        f"Тема: {o[7]}\n"
        f"Предмет: {o[8]}\n"
        f"Дедлайн: {o[9]}\n"
        f"Об'єм: {o[10]}\n"
        f"Вимоги: {o[11]}\n"
        f"Ціна: {o[13]} грн\n"
        f"Статус: {o[14]}\n"
        f"user_id: {o[1]}\n"
        f"Ім'я: {o[2]}\n"
        f"username: @{o[3]}\n"
        f"Телефон: {o[4]}\n"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("find"))
async def admin_find(message: types.Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.answer("⛔ Тільки адміністратор може шукати замовлення.")
        return
    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        await message.answer("Використання: /find <user_id|username|тема>")
        return
    query = args[1].lower()
    found = find_orders(query)
    if not found:
        await message.answer("Нічого не знайдено.")
        return
    text = "<b>Результати пошуку:</b>\n"
    for i, o in enumerate(found, 1):
        text += (
            f"\n<b>{i} (ID:{o[0]})</b> {o[6]}\n"
            f"Тема: {o[8]}\n"
            f"Дедлайн: {o[10]}\n"
            f"Ціна: {o[13]} грн\n"
            f"Статус: {o[14]}\n"
            f"user_id: {o[1]}\n"
        )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("stats"))
async def admin_stats(message: types.Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.answer("⛔ Тільки адміністратор може переглядати статистику.")
        return
    orders = get_orders()
    if not orders:
        await message.answer("Замовлень ще немає.")
        return
    # Загальна кількість
    total = len(orders)
    # Кількість за статусами
    status_counter = Counter(o[14] for o in orders)
    # ТОП-5 типів робіт
    type_counter = Counter(o[6] for o in orders)
    # ТОП-5 предметів
    subject_counter = Counter(o[9] for o in orders)
    # Середній чек
    prices = [int(o[13]) for o in orders if str(o[13]).isdigit()]
    avg_price = int(sum(prices) / len(prices)) if prices else 0
    # Унікальні користувачі
    users = set(o[2] for o in orders)
    # Замовлення за останній місяць/тиждень
    now = datetime.now().date()
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)
    orders_month = [o for o in orders if o[10] and o[10] >= str(month_ago)]
    orders_week = [o for o in orders if o[10] and o[10] >= str(week_ago)]
    # Формуємо текст
    text = f"<b>Статистика замовлень:</b>\n"
    text += f"Всього замовлень: <b>{total}</b>\n"
    text += "\n<b>За статусами:</b>\n" + "\n".join(f"{k}: {v}" for k, v in status_counter.items())
    text += "\n\n<b>ТОП-5 типів робіт:</b>\n" + "\n".join(f"{k}: {v}" for k, v in type_counter.most_common(5))
    text += "\n\n<b>ТОП-5 предметів:</b>\n" + "\n".join(f"{k}: {v}" for k, v in subject_counter.most_common(5))
    text += f"\n\nСередній чек: <b>{avg_price} грн</b>\n"
    text += f"Унікальних користувачів: <b>{len(users)}</b>\n"
    text += f"Замовлень за місяць: <b>{len(orders_month)}</b>\n"
    text += f"Замовлень за тиждень: <b>{len(orders_week)}</b>\n"
    await message.answer(text, parse_mode="HTML")

@router.message(Command("addpromo"))
async def addpromo_handler(message: types.Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.answer("⛔ Тільки адміністратор може створювати промокоди.")
        return
    args = message.text.split()
    if len(args) != 5:
        await message.answer("Використання: /addpromo <код> <тип> <значення> <ліміт>\nТип: percent або fixed\nНаприклад: /addpromo SUMMER2024 percent 10 100")
        return
    code, discount_type, discount_value, usage_limit = args[1], args[2], int(args[3]), int(args[4])
    if discount_type not in ("percent", "fixed"):
        await message.answer("Тип знижки має бути percent або fixed.")
        return
    add_promocode(code.upper(), discount_type, discount_value, usage_limit)
    await message.answer(f"Промокод {code.upper()} створено!")

@router.message(Command("promos"))
async def promos_handler(message: types.Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.answer("⛔ Тільки адміністратор може переглядати промокоди.")
        return
    # Виводимо всі промокоди та статистику використань
    text = "<b>Промокоди:</b>\n"
    # Для простоти — отримуємо всі промокоди через get_orders і шукаємо унікальні коди
    orders = get_orders()
    codes = set()
    for o in orders:
        promo = o[15] if len(o) > 15 else None
        if promo:
            codes.add(promo)
    if not codes:
        text += "Промокодів ще не використовували."
    for code in codes:
        promo = get_promocode(code)
        usages = get_promocode_usages(code)
        if promo:
            text += (f"\n<b>{promo[0]}</b>: {promo[1]} {promo[2]} (ліміт: {promo[3]}, використано: {promo[4]})\n"
                      f"Використань: {len(usages)}\n")
    await message.answer(text, parse_mode="HTML")

@router.message(Command(re.compile(r"setstatus_(\d+)_(\w+)")))
async def setstatus_handler_underscore(message: types.Message, command: CommandObject, bot: Bot):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.answer("⛔ Тільки адміністратор може змінювати статуси.")
        return
    try:
        parts = command.command.split('_')
        order_num = int(parts[1])
        new_status = parts[2]
    except Exception:
        await message.answer("Невірний формат команди. Приклад: /setstatus_5_done")
        return
    ok, order_id = update_order_status(order_num, new_status)
    if not ok:
        await message.answer("Замовлення з таким номером не знайдено.")
        return
    o = get_order_by_num(order_num)
    user_id = o[1]
    try:
        await bot.send_message(user_id, f"Статус вашого замовлення №{order_num} змінено на: <b>{new_status}</b>", parse_mode="HTML")
        if new_status in ["готове", "оплачено", "done", "paid"]:
            await request_feedback(user_id, bot)
    except Exception:
        await message.answer("Не вдалося надіслати сповіщення користувачу.")
    await message.answer(f"Статус замовлення №{order_num} змінено на {new_status}.")

class AdminMsgStates(StatesGroup):
    waiting_for_text = State()

@router.message(Command(re.compile(r"msg_(\d+)")))
async def admin_msg_start(message: types.Message, command: CommandObject, state: FSMContext):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.answer("⛔ Тільки адміністратор може писати користувачам.")
        return
    try:
        user_id = int(command.command.split('_')[1])
    except Exception:
        await message.answer("Невірний формат команди. Приклад: /msg_123456789")
        return
    await state.update_data(target_user_id=user_id)
    await message.answer(f"Введіть текст повідомлення для користувача <code>{user_id}</code>:", parse_mode="HTML")
    await state.set_state(AdminMsgStates.waiting_for_text)

@router.message(AdminMsgStates.waiting_for_text)
async def admin_msg_send(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = data.get('target_user_id')
    try:
        await bot.send_message(user_id, f"<b>Повідомлення від адміністратора:</b>\n{message.text}", parse_mode="HTML")
        await message.answer("Повідомлення надіслано користувачу.")
    except Exception:
        await message.answer("Не вдалося надіслати повідомлення користувачу. Можливо, він не писав боту.")
    await state.clear() 
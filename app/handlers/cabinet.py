import json
import os
from aiogram import types, Router
from aiogram.filters import Command
from aiogram import Bot
from app.config import Config, ORDER_STATUSES, STATUS_COLORS, SPAM_LIMITS
# from app.handlers.feedback import request_feedback
from collections import Counter
from datetime import datetime, timedelta
from app.db import (
    get_orders, get_order_by_num, find_orders, update_order_status, 
    add_promocode, get_promocode, get_promocode_usages, get_order_by_id,
    create_backup, check_spam_protection, log_message
)
import re
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.utils.validation import delete_previous_messages, delete_all_tracked_messages, is_command

router = Router()

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirmation = State()

def get_admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📢 Масові розсилки", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="💾 Створити бекап", callback_data="admin_backup")],
            [InlineKeyboardButton(text="🎫 Управління промокодами", callback_data="admin_promos")],
            [InlineKeyboardButton(text="🔧 Налаштування", callback_data="admin_settings")]
        ]
    )

@router.message(Command("cabinet"))
async def cabinet_handler(message: types.Message, state: FSMContext):
    await delete_all_tracked_messages(message.bot, message.chat.id, state)
    await state.update_data(last_user_message_id=message.message_id)
    user_id = message.from_user.id
    try:
        data = await state.get_data()
        last_info_id = data.get('last_info_message_id')
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        try:
            await message.delete()
        except Exception as del_exc:
            print(f"[WARNING] /cabinet: не вдалося видалити повідомлення: {del_exc}")
        if user_id in Config.ADMIN_IDS:
            print(f"[INFO] /cabinet: admin {user_id} - перенаправлено на /cabinet_ad")
            sent = await message.answer("❗️ Для адміністратора використовуйте /cabinet_ad", parse_mode="HTML")
            await state.update_data(last_info_message_id=sent.message_id)
            return
        # Звичайний користувач
        orders = get_orders(user_id=user_id)
        if not orders:
            print(f"[INFO] /cabinet: user {user_id} - немає замовлень")
            sent = await message.answer(
                "📋 <b>Мої замовлення</b>\n\n"
                "У вас поки немає замовлень.\n"
                "Створіть перше замовлення командою /order",
                parse_mode="HTML"
            )
            await state.update_data(last_info_message_id=sent.message_id)
            return
        text = "📋 <b>Мої замовлення:</b>\n\n"
        for order in orders[:10]:  # Показуємо останні 10
            order_id, _, _, _, _, type_label, _, topic, _, deadline, _, _, _, price, status, created_at = order[:16]
            status_emoji = STATUS_COLORS.get(status, "⚪")
            status_text = ORDER_STATUSES.get(status, status)
            text += f"{status_emoji} <b>#{order_id}</b> - {type_label}\n"
            text += f"📖 {topic[:50]}{'...' if len(topic) > 50 else ''}\n"
            text += f"💰 {price} грн | 📅 {deadline}\n"
            text += f"📊 Статус: {status_text}\n\n"
        if len(orders) > 10:
            text += f"... та ще {len(orders) - 10} замовлень"
        sent = await message.answer(text, parse_mode="HTML", reply_markup=None)
        await state.update_data(last_bot_message_id=sent.message_id)
        print(f"[INFO] /cabinet: user {user_id} - показано {len(orders)} замовлень")
    except Exception as e:
        print(f"[ERROR] /cabinet: user {user_id} - {e}")
        sent = await message.answer("Сталася помилка при отриманні кабінету.")
        await state.update_data(last_bot_message_id=sent.message_id)

@router.message(Command("cabinet_ad"))
async def cabinet_admin_handler(message: types.Message):
    user_id = message.from_user.id
    try:
        await message.delete()
    except Exception as del_exc:
        print(f"[WARNING] /cabinet_ad: не вдалося видалити повідомлення: {del_exc}")
    if user_id not in Config.ADMIN_IDS:
        print(f"[ERROR] /cabinet_ad: user {user_id} не є адміністратором")
        await message.answer("⛔️ Доступ лише для адміністратора", parse_mode="HTML")
        return
    keyboard = get_admin_keyboard()
    await message.answer(
        "🔧 <b>Адміністративний кабінет</b>\n\n"
        "Оберіть потрібну функцію:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    print(f"[INFO] /cabinet_ad: admin {user_id} - відкрито адмін-кабінет")

@router.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats_callback(callback: types.CallbackQuery):
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("Доступ заборонено")
        return
    
    # Збираємо статистику
    all_orders = get_orders()
    total_orders = len(all_orders)
    
    # Статистика за статусами
    status_counts = Counter(order[14] for order in all_orders)
    
    # Статистика за типами
    type_counts = Counter(order[5] for order in all_orders)
    
    # Статистика за останні 7 днів
    week_ago = datetime.now() - timedelta(days=7)
    recent_orders = [order for order in all_orders 
                    if datetime.fromisoformat(order[15]) > week_ago]
    
    # Загальна вартість
    total_revenue = sum(order[13] for order in all_orders if order[13])
    
    stats_text = f"""
📊 <b>Статистика бота</b>

📈 <b>Загальна статистика:</b>
• Всього замовлень: {total_orders}
• Загальна вартість: {total_revenue} грн
• За останні 7 днів: {len(recent_orders)}

📋 <b>За статусами:</b>
"""
    
    for status, count in status_counts.most_common():
        status_emoji = STATUS_COLORS.get(status, "⚪")
        status_text = ORDER_STATUSES.get(status, status)
        stats_text += f"{status_emoji} {status_text}: {count}\n"
    
    stats_text += "\n📝 <b>За типами робіт:</b>\n"
    for order_type, count in type_counts.most_common():
        stats_text += f"• {order_type}: {count}\n"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Експорт статистики", callback_data="export_stats")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]
        ]
    )
    
    await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_callback(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("Доступ заборонено")
        return
    
    await state.set_state(BroadcastStates.waiting_for_message)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]]
    )
    await callback.message.edit_text(
        "📢 <b>Масові розсилки</b>\n\n"
        "Надішліть повідомлення для розсилки.\n"
        "Підтримуються: текст, фото, відео, документи\n\n"
        "Для скасування напишіть /cancel",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Розсилка скасована")
        return
    
    # Зберігаємо повідомлення
    await state.update_data(
        message_type=message.content_type,
        text=message.text if message.text else message.caption,
        file_id=message.document.file_id if message.document else None,
        photo_id=message.photo[-1].file_id if message.photo else None,
        video_id=message.video.file_id if message.video else None
    )
    
    # Показуємо підтвердження
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Підтвердити", callback_data="confirm_broadcast")],
            [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_broadcast")]
        ]
    )
    
    preview_text = f"""
📢 <b>Попередній перегляд розсилки:</b>

{message.text or message.caption or 'Медіа повідомлення'}

---
Користувачів для розсилки: {len(set(order[1] for order in get_orders()))}
"""
    
    await message.answer(preview_text, parse_mode="HTML", reply_markup=keyboard)
    await state.set_state(BroadcastStates.waiting_for_confirmation)

@router.callback_query(lambda c: c.data == "confirm_broadcast")
async def confirm_broadcast_callback(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("Доступ заборонено")
        return
    
    data = await state.get_data()
    
    # Отримуємо унікальних користувачів
    orders = get_orders()
    users = set(order[1] for order in orders)
    
    sent_count = 0
    failed_count = 0
    
    for user_id in users:
        try:
            if data['message_type'] == 'text':
                await callback.bot.send_message(user_id, data['text'], parse_mode="HTML")
            elif data['message_type'] == 'document':
                await callback.bot.send_document(user_id, data['file_id'], caption=data['text'])
            elif data['message_type'] == 'photo':
                await callback.bot.send_photo(user_id, data['photo_id'], caption=data['text'])
            elif data['message_type'] == 'video':
                await callback.bot.send_video(user_id, data['video_id'], caption=data['text'])
            
            sent_count += 1
            
        except Exception as e:
            failed_count += 1
            print(f"Помилка відправки користувачу {user_id}: {e}")
    
    await callback.message.edit_text(
        f"✅ <b>Розсилка завершена!</b>\n\n"
        f"📤 Відправлено: {sent_count}\n"
        f"❌ Помилки: {failed_count}\n"
        f"📊 Всього користувачів: {len(users)}",
        parse_mode="HTML"
    )
    
    await state.clear()
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_backup")
async def admin_backup_callback(callback: types.CallbackQuery):
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("Доступ заборонено")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]]
    )
    try:
        backup_file = create_backup()
        await callback.message.edit_text(
            f"✅ <b>Бекап створено!</b>\n\n"
            f"📁 Файл: {backup_file}\n"
            f"📅 Час: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Помилка створення бекапу:</b>\n{str(e)}",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_promos")
async def admin_promos_callback(callback: types.CallbackQuery):
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("Доступ заборонено")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Додати промокод", callback_data="add_promo")],
            [InlineKeyboardButton(text="📊 Статистика промокодів", callback_data="promo_stats")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]
        ]
    )
    
    await callback.message.edit_text(
        "🎫 <b>Управління промокодами</b>\n\n"
        "Оберіть потрібну функцію:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "promo_stats")
async def promo_stats_callback(callback: types.CallbackQuery):
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("Доступ заборонено")
        return
    
    # Отримуємо статистику промокодів
    promocodes = []
    import sqlite3
    conn = sqlite3.connect('botdata.sqlite3')
    c = conn.cursor()
    c.execute('SELECT * FROM promocodes')
    promocodes = c.fetchall()
    conn.close()
    
    if not promocodes:
        await callback.message.edit_text(
            "📊 <b>Статистика промокодів</b>\n\n"
            "Промокодів не знайдено.",
            parse_mode="HTML"
        )
        return
    
    stats_text = "📊 <b>Статистика промокодів:</b>\n\n"
    
    for promo in promocodes:
        code, discount_type, discount_value, usage_limit, used_count, created_at, expires_at, is_personal, personal_user_id, min_order_amount = promo
        
        stats_text += f"🎫 <b>{code}</b>\n"
        stats_text += f"💰 {discount_value} {'%' if discount_type == 'percent' else 'грн'}\n"
        stats_text += f"📊 Використано: {used_count}/{usage_limit or '∞'}\n"
        
        if expires_at:
            stats_text += f"⏰ Діє до: {expires_at[:10]}\n"
        
        if is_personal:
            stats_text += f"👤 Персональний для: {personal_user_id}\n"
        
        if min_order_amount:
            stats_text += f"💳 Мін. сума: {min_order_amount} грн\n"
        
        stats_text += "\n"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_promos")]
        ]
    )
    
    await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(lambda c: c.data == "back_to_admin")
async def back_to_admin_callback(callback: types.CallbackQuery):
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("Доступ заборонено")
        return
    
    keyboard = get_admin_keyboard()
    await callback.message.edit_text(
        "🔧 <b>Адміністративний кабінет</b>\n\n"
        "Оберіть потрібну функцію:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

# Інші обробники залишаються без змін
@router.message(Command("orders"))
async def orders_handler(message: types.Message, state: FSMContext):
    if message.from_user.id not in Config.ADMIN_IDS:
        return
    try:
        await message.delete()
    except Exception as del_exc:
        print(f"[WARNING] /orders: не вдалося видалити повідомлення: {del_exc}")
    data = await state.get_data()
    last_info_id = data.get('last_info_message_id')
    if last_info_id:
        try:
            await message.bot.delete_message(message.chat.id, last_info_id)
        except: pass
    orders = get_orders()
    
    if not orders:
        sent = await message.answer("Замовлень не знайдено.")
        await state.update_data(last_info_message_id=sent.message_id)
        return
    
    text = f"📋 <b>Всі замовлення ({len(orders)}):</b>\n\n"
    
    for order in orders[:20]:  # Показуємо перші 20
        order_id, user_id, first_name, username, _, type_label, _, topic, _, deadline, _, _, _, price, status, created_at = order[:16]
        
        status_emoji = STATUS_COLORS.get(status, "⚪")
        status_text = ORDER_STATUSES.get(status, status)
        
        text += f"{status_emoji} <b>#{order_id}</b> - {type_label}\n"
        text += f"👤 {first_name} (@{username})\n"
        text += f"📖 {topic[:50]}{'...' if len(topic) > 50 else ''}\n"
        text += f"💰 {price} грн | 📅 {deadline}\n"
        text += f"📊 Статус: {status_text}\n\n"
    
    if len(orders) > 20:
        text += f"... та ще {len(orders) - 20} замовлень"
    sent = await message.answer(text, parse_mode="HTML")
    await state.update_data(last_info_message_id=sent.message_id)

@router.message(Command("order"))
async def order_detail_handler(message: types.Message, command: CommandObject, state: FSMContext):
    if message.from_user.id not in Config.ADMIN_IDS:
        return
    try:
        await message.delete()
    except Exception as del_exc:
        print(f"[WARNING] /order: не вдалося видалити повідомлення: {del_exc}")
    data = await state.get_data()
    last_info_id = data.get('last_info_message_id')
    if last_info_id:
        try:
            await message.bot.delete_message(message.chat.id, last_info_id)
        except: pass
    if not command.args:
        sent = await message.answer("Використання: /order <номер>")
        await state.update_data(last_info_message_id=sent.message_id)
        return
    
    try:
        order_num = int(command.args)
        order_data = get_order_by_id(order_num)
        
        if not order_data:
            sent = await message.answer(f"Замовлення #{order_num} не знайдено.")
            await state.update_data(last_info_message_id=sent.message_id)
            return
        
        order = order_data['order']
        files = order_data['files']
        status_history = order_data['status_history']
        
        order_id, user_id, first_name, username, phone, type_label, order_type, topic, subject, deadline, volume, requirements, files_json, price, status, created_at, updated_at, confirmed_at, manager_id, notes = order
        
        status_emoji = STATUS_COLORS.get(status, "⚪")
        status_text = ORDER_STATUSES.get(status, status)
        
        text = f"""
📋 <b>Замовлення #{order_id}</b>

👤 <b>Користувач:</b>
• Ім'я: {first_name}
• Username: @{username}
• ID: {user_id}
• Телефон: {phone}

📝 <b>Деталі замовлення:</b>
• Тип: {type_label}
• Тема: {topic}
• Предмет: {subject}
• Термін: {deadline}
• Обсяг: {volume}
• Вимоги: {requirements}

💰 <b>Фінанси:</b>
• Ціна: {price} грн
• Статус: {status_emoji} {status_text}

📎 <b>Файли:</b> {len(files)} шт.

📅 <b>Дати:</b>
• Створено: {created_at[:10]}
• Оновлено: {updated_at[:10] if updated_at else 'Ні'}

📝 <b>Примітки:</b> {notes or 'Немає'}
"""
        
        # Клавіатура для зміни статусу
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"{emoji} {text}", callback_data=f"set_status:{order_id}:{status_code}")]
                for status_code, text in ORDER_STATUSES.items()
            ] + [
                [InlineKeyboardButton(text="💬 Написати користувачу", callback_data=f"msg_user:{user_id}")],
                [InlineKeyboardButton(text="📊 Історія статусів", callback_data=f"status_history:{order_id}")]
            ]
        )
        
        sent = await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        await state.update_data(last_info_message_id=sent.message_id)
        
    except ValueError:
        sent = await message.answer("Невірний номер замовлення.")
        await state.update_data(last_info_message_id=sent.message_id)

@router.message(Command("setstatus"))
async def set_status_handler(message: types.Message, command: CommandObject, state: FSMContext):
    if message.from_user.id not in Config.ADMIN_IDS:
        return
    try:
        await message.delete()
    except Exception as del_exc:
        print(f"[WARNING] /setstatus: не вдалося видалити повідомлення: {del_exc}")
    data = await state.get_data()
    last_info_id = data.get('last_info_message_id')
    if last_info_id:
        try:
            await message.bot.delete_message(message.chat.id, last_info_id)
        except: pass
    args = command.args.split('_')
    if len(args) != 2:
        sent = await message.answer("Використання: /setstatus <номер>_<статус>")
        await state.update_data(last_info_message_id=sent.message_id)
        return
    
    try:
        order_id = int(args[0])
        new_status = args[1]
        
        if new_status not in ORDER_STATUSES:
            sent = await message.answer(f"Невірний статус. Доступні: {', '.join(ORDER_STATUSES.keys())}")
            await state.update_data(last_info_message_id=sent.message_id)
            return
        
        update_order_status(order_id, new_status, message.from_user.id, "Змінено через команду")
        
        sent = await message.answer(f"✅ Статус замовлення #{order_id} змінено на '{ORDER_STATUSES[new_status]}'")
        await state.update_data(last_info_message_id=sent.message_id)
        
    except ValueError:
        sent = await message.answer("Невірний формат команди.")
        await state.update_data(last_info_message_id=sent.message_id)

@router.message(Command("stats"))
async def stats_handler(message: types.Message, state: FSMContext):
    if message.from_user.id not in Config.ADMIN_IDS:
        return
    try:
        await message.delete()
    except Exception as del_exc:
        print(f"[WARNING] /stats: не вдалося видалити повідомлення: {del_exc}")
    data = await state.get_data()
    last_info_id = data.get('last_info_message_id')
    if last_info_id:
        try:
            await message.bot.delete_message(message.chat.id, last_info_id)
        except: pass
    orders = get_orders()
    
    if not orders:
        sent = await message.answer("Статистика недоступна - немає замовлень.")
        await state.update_data(last_info_message_id=sent.message_id)
        return
    
    # Базова статистика
    total_orders = len(orders)
    total_revenue = sum(order[13] for order in orders if order[13])
    
    # Статистика за статусами
    status_counts = Counter(order[14] for order in orders)
    
    # Статистика за останні 7 днів
    week_ago = datetime.now() - timedelta(days=7)
    recent_orders = [order for order in orders 
                    if datetime.fromisoformat(order[15]) > week_ago]
    
    text = f"""
📊 <b>Статистика бота</b>

📈 <b>Загальна статистика:</b>
• Всього замовлень: {total_orders}
• Загальна вартість: {total_revenue} грн
• За останні 7 днів: {len(recent_orders)}

📋 <b>За статусами:</b>
"""
    
    for status, count in status_counts.most_common():
        status_emoji = STATUS_COLORS.get(status, "⚪")
        status_text = ORDER_STATUSES.get(status, status)
        text += f"{status_emoji} {status_text}: {count}\n"
    
    sent = await message.answer(text, parse_mode="HTML")
    await state.update_data(last_info_message_id=sent.message_id)

@router.message(Command("addpromo"))
async def add_promo_handler(message: types.Message, command: CommandObject, state: FSMContext):
    if message.from_user.id not in Config.ADMIN_IDS:
        return
    try:
        await message.delete()
    except Exception as del_exc:
        print(f"[WARNING] /addpromo: не вдалося видалити повідомлення: {del_exc}")
    data = await state.get_data()
    last_info_id = data.get('last_info_message_id')
    if last_info_id:
        try:
            await message.bot.delete_message(message.chat.id, last_info_id)
        except: pass
    args = command.args.split('_')
    if len(args) < 4:
        sent = await message.answer("Використання: /addpromo <код>_<тип>_<значення>_<ліміт>_[термін_дії]")
        await state.update_data(last_info_message_id=sent.message_id)
        return
    
    try:
        code = args[0].upper()
        discount_type = args[1]
        discount_value = int(args[2])
        usage_limit = int(args[3])
        expires_at = args[4] if len(args) > 4 else None
        
        add_promocode(code, discount_type, discount_value, usage_limit, expires_at)
        
        sent = await message.answer(f"✅ Промокод {code} додано!")
        await state.update_data(last_info_message_id=sent.message_id)
        
    except (ValueError, IndexError):
        sent = await message.answer("Невірний формат команди.")
        await state.update_data(last_info_message_id=sent.message_id)

@router.message(Command("promos"))
async def promos_handler(message: types.Message, state: FSMContext):
    if message.from_user.id not in Config.ADMIN_IDS:
        return
    try:
        await message.delete()
    except Exception as del_exc:
        print(f"[WARNING] /promos: не вдалося видалити повідомлення: {del_exc}")
    data = await state.get_data()
    last_info_id = data.get('last_info_message_id')
    if last_info_id:
        try:
            await message.bot.delete_message(message.chat.id, last_info_id)
        except: pass
    # Отримуємо статистику промокодів
    promocodes = []
    import sqlite3
    conn = sqlite3.connect('botdata.sqlite3')
    c = conn.cursor()
    c.execute('SELECT * FROM promocodes')
    promocodes = c.fetchall()
    conn.close()
    
    if not promocodes:
        sent = await message.answer("Промокодів не знайдено.")
        await state.update_data(last_info_message_id=sent.message_id)
        return
    
    text = "📊 <b>Статистика промокодів:</b>\n\n"
    
    for promo in promocodes:
        code, discount_type, discount_value, usage_limit, used_count, created_at, expires_at, is_personal, personal_user_id, min_order_amount = promo
        
        text += f"🎫 <b>{code}</b>\n"
        text += f"💰 {discount_value} {'%' if discount_type == 'percent' else 'грн'}\n"
        text += f"📊 Використано: {used_count}/{usage_limit or '∞'}\n"
        
        if expires_at:
            text += f"⏰ Діє до: {expires_at[:10]}\n"
        
        text += "\n"
    
    sent = await message.answer(text, parse_mode="HTML")
    await state.update_data(last_info_message_id=sent.message_id)

@router.message(Command("feedbacks"))
async def feedbacks_handler(message: types.Message, state: FSMContext):
    if message.from_user.id not in Config.ADMIN_IDS:
        return
    try:
        await message.delete()
    except Exception as del_exc:
        print(f"[WARNING] /feedbacks: не вдалося видалити повідомлення: {del_exc}")
    data = await state.get_data()
    last_info_id = data.get('last_info_message_id')
    if last_info_id:
        try:
            await message.bot.delete_message(message.chat.id, last_info_id)
        except: pass
    # Отримуємо відгуки
    feedbacks = []
    import sqlite3
    conn = sqlite3.connect('botdata.sqlite3')
    c = conn.cursor()
    c.execute('SELECT * FROM feedbacks ORDER BY created_at DESC')
    feedbacks = c.fetchall()
    conn.close()
    
    if not feedbacks:
        sent = await message.answer("Відгуків не знайдено.")
        await state.update_data(last_info_message_id=sent.message_id)
        return
    
    text = f"📝 <b>Всі відгуки ({len(feedbacks)}):</b>\n\n"
    
    for feedback in feedbacks[:10]:  # Показуємо останні 10
        feedback_id, user_id, username, text_content, stars, created_at = feedback
        
        text += f"⭐ <b>{'⭐' * stars}{'☆' * (5 - stars)}</b>\n"
        text += f"👤 @{username} (ID: {user_id})\n"
        text += f"📝 {text_content[:100]}{'...' if len(text_content) > 100 else ''}\n"
        text += f"📅 {created_at[:10]}\n\n"
    
    if len(feedbacks) > 10:
        text += f"... та ще {len(feedbacks) - 10} відгуків"
    
    sent = await message.answer(text, parse_mode="HTML")
    await state.update_data(last_info_message_id=sent.message_id)

@router.callback_query(lambda c: c.data == "user_stats")
async def user_stats_callback(callback: types.CallbackQuery):
    try:
        # Тут можна реалізувати реальну статистику користувача
        await callback.message.answer("📊 Детальна статистика буде доступна найближчим часом.")
        await callback.answer()
        print(f"[INFO] Кабінет: користувач {callback.from_user.id} натиснув 'Детальна статистика'")
    except Exception as e:
        print(f"[ERROR] Кабінет: user_stats для {callback.from_user.id} - {e}")
        await callback.message.answer("Сталася помилка при отриманні статистики.")
        await callback.answer() 
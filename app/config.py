import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    # Список id адміністраторів через кому, наприклад: 123456789,987654321
    ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

# Цінова політика для різних типів робіт
ORDER_TYPE_PRICES = {
    "coursework": {"base": 1000, "per_page": 40, "label": "Курсова робота"},
    "labwork": {"base": 200, "per_work": 30, "label": "Лабораторна робота"},
    "essay": {"base": 300, "per_page": 15, "label": "Реферат"},
    "testwork": {"base": 250, "per_work": 25, "label": "Контрольна робота"},
    "other": {"base": 400, "per_page": 20, "label": "Інше"},
} 
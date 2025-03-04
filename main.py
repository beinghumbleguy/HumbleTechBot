from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
import logging
import os
import re
from flask import Flask
from threading import Thread

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN not set!")
    raise ValueError("BOT_TOKEN is required")

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

@app.route('/')
def home():
    logger.info("Flask route '/' accessed")
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))  # Railway defaults to 5000
    logger.info(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

@dp.message(F.text)
async def convert_link_to_button(message: types.Message):
    if message.entities:
        text = message.text
        ca = None
        for entity in message.entities:
            if entity.type == "url":
                url = text[entity.offset:entity.offset + entity.length]
                ca_match = re.search(r'[A-Za-z0-9]{44}', url)
                if ca_match:
                    ca = ca_match.group(0)
                break

        if ca:
            # Buttons side by side in one row
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Trojan", url=f"https://t.me/solana_trojanbot?start=r-beinghumbleguy-{ca}"),
                    InlineKeyboardButton(text="Maestro", url=f"http://t.me/maestro?start={ca}-beinghumbleguy"),
                    InlineKeyboardButton(text="Fasol", url=f"https://t.me/fasol_robot?start=ref_beinghumbleguy_ca_{ca}")
                ]
            ])
            text = re.sub(r'Buy token on Fasol Reflink', '', text, flags=re.IGNORECASE).strip()
            try:
                await message.answer(text, reply_markup=keyboard)
                await message.delete()
            except Exception as e:
                logger.error(f"Error processing message: {e}")

async def main():
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
import asyncio
import logging
import os
import re
from flask import Flask
from threading import Thread

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
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

@dp.message(F.text)
@dp.channel_post(F.text)
async def convert_link_to_button(message: types.Message):
    logger.info(f"Received message: {message.text}")
    logger.info(f"Chat type: {message.chat.type}")
    logger.info(f"Forwarded from: {message.forward_from_chat}")
    logger.info(f"Entities: {message.entities}")

    if message.forward_from_chat:
        logger.info(f"Message is forwarded from chat: {message.forward_from_chat.title}")

    if message.entities:
        text = message.text
        ca = None
        url_to_preserve = None
        ca_original_offset = None
        ca_length = None

        # Step 1: Extract CA and its position from the original message
        for entity in message.entities:
            if entity.type in ["url", "text_link"]:
                url = entity.url if entity.type == "text_link" else text[entity.offset:entity.offset + entity.length]
                logger.info(f"Found URL: {url}")
                ca_match = re.search(r'[A-Za-z0-9]{44}', url)
                if ca_match:
                    ca = ca_match.group(0)
                    url_to_preserve = url
                    logger.info(f"Extracted CA: {ca}")
                break
            elif entity.type == "code":  # Capture CA's original position if it has a code entity
                ca_text = text[entity.offset:entity.offset + entity.length]
                if ca_text == ca:  # Ensure this matches the CA from the URL
                    ca_original_offset = entity.offset
                    ca_length = entity.length

        if ca:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Trojan", url=f"https://t.me/solana_trojanbot?start=r-beinghumbleguy-{ca}"),
                    InlineKeyboardButton(text="Maestro", url=f"http://t.me/maestro?start={ca}-beinghumbleguy"),
                    InlineKeyboardButton(text="Fasol", url=f"https://t.me/fasol_robot?start=ref_beinghumbleguy_ca_{ca}")
                ]
            ])
            # Step 2: Clean the text but keep the URL
            text = re.sub(r'Forwarded from .*\n', '', text, flags=re.IGNORECASE)
            text = re.sub(r'Buy token on Fasol Reflink', '', text, flags=re.IGNORECASE).strip()
            text = f"{text}\n\n🔗 {url_to_preserve}"
            logger.info(f"Final text to send: {text}")

            # Step 3: Calculate the new offset of the CA in the final text
            entities = []
            if ca_length:  # If CA had a code entity in the original message
                # Find the CA's new position in the cleaned text
                ca_new_offset = text.rfind(ca)  # Find the last occurrence of CA in the final text
                if ca_new_offset >= 0:
                    # Validate the offset in UTF-16 (Telegram uses UTF-16 for offsets)
                    text_length_utf16 = len(text.encode('utf-16-le')) // 2
                    if ca_new_offset + ca_length <= text_length_utf16:
                        entities.append(MessageEntity(type="code", offset=ca_new_offset, length=ca_length))
                        logger.info(f"Applied code entity: Offset {ca_new_offset}, Length {ca_length}")
                    else:
                        logger.warning(f"Skipping invalid code entity: Offset {ca_new_offset}, Length {ca_length}")

            try:
                await message.answer(text, reply_markup=keyboard, entities=entities)
                await message.delete()
            except Exception as e:
                logger.error(f"Error processing message: {e}")
        else:
            logger.info("No CA found in URL")

async def main():
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

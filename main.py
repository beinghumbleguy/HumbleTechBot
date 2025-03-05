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
    logger.info(f"Original message ID: {message.message_id}")
    logger.info(f"Forwarded from: {message.forward_from_chat}")
    logger.info(f"Entities: {message.entities}")

    if message.forward_from_chat:
        logger.info(f"Message is forwarded from chat: {message.forward_from_chat.title}")

    if message.entities:
        text = message.text
        ca = None
        for entity in message.entities:
            if entity.type in ["url", "text_link"]:
                url = entity.url if entity.type == "text_link" else text[entity.offset:entity.offset + entity.length]
                logger.info(f"Found URL: {url}")
                ca_match = re.search(r'[A-Za-z0-9]{44}', url)
                if ca_match:
                    ca = ca_match.group(0)
                    logger.info(f"Extracted CA: {ca}")
                break

        if ca:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Bloom", url=f"https://t.me/BloomSolana_bot?start=ref_humbleguy_ca_{ca}"),
                    InlineKeyboardButton(text="Fasol", url=f"https://t.me/fasol_robot?start=ref_humbleguy_ca_{ca}")  
                ],
                [
                    InlineKeyboardButton(text="Maestro", url=f"http://t.me/maestro?start={ca}-beinghumbleguy"),
                    InlineKeyboardButton(text="Trojan", url=f"https://t.me/solana_trojanbot?start=r-beinghumbleguy-{ca}")
                ]
            ])
            # Clean the text (remove "Forwarded from" and "Buy token on Fasol Reflink")
            text = re.sub(r'Forwarded from .*\n', '', text, flags=re.IGNORECASE)
            text = re.sub(r'Buy token on Fasol Reflink', '', text, flags=re.IGNORECASE)
            # Format the CA line to match the alignment of other lines
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if ca in line:
                    lines[i] = f"🔗 CA: {ca}"  # Align with other lines like "💎 MC: $29.5k"
                    break
            text = "\n".join(line.strip() for line in lines if line.strip())
            logger.info(f"Final text to send: {text}")

            # Apply the code entity to the CA only (excluding the emoji and "CA: ")
            entities = []
            ca_new_offset = text.find(ca)  # Find CA's position in final text
            if ca_new_offset >= 0:
                ca_length = 44  # Hardcode length since CA is always 44 characters
                # Adjust offset for "🔗 CA: " (emoji is 2 UTF-16 chars, " CA: " is 5 chars)
                ca_new_offset += 7  # 2 for emoji, 5 for " CA: "
                text_length_utf16 = len(text.encode('utf-16-le')) // 2
                if ca_new_offset + ca_length <= text_length_utf16:
                    entities.append(MessageEntity(type="code", offset=ca_new_offset, length=ca_length))
                    logger.info(f"Applied code entity: Offset {ca_new_offset}, Length {ca_length}")
                else:
                    logger.warning(f"Skipping invalid code entity: Offset {ca_new_offset}, Length {ca_length}")

            try:
                edited_message = await message.edit_text(text, reply_markup=keyboard, entities=entities)
                logger.info(f"Edited message ID: {edited_message.message_id}")
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                await message.answer(text, reply_markup=keyboard, entities=entities)
                try:
                    await message.delete()
                except Exception as delete_error:
                    logger.warning(f"Could not delete original message: {delete_error}")
        else:
            logger.info("No CA found in URL")

async def main():
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
import asyncio
import logging
import os
import re
from flask import Flask
from threading import Thread

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load bot token from environment variable (Railway app)
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN not set!")
    raise ValueError("BOT_TOKEN is required")

# Initialize Bot and Dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = Flask(__name__)

# Global variable to track filter state
filter_enabled = False

# Flask route
@app.route('/')
def home():
    logger.info("Flask route '/' accessed")
    return "Bot is running!"

# Function to run Flask app in a separate thread
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

# Handler for /filter command to enable/disable filter
@dp.message_handler(commands=["filter"])
async def toggle_filter(message: types.Message):
    global filter_enabled
    text = message.text.lower().replace('/filter', '').strip()
    logger.info(f"Received /filter command with text: {text}")

    if text == "yes":
        filter_enabled = True
        await message.answer("Filter enabled.")
        logger.info("Filter enabled")
    elif text == "no":
        filter_enabled = False
        await message.answer("Filter disabled.")
        logger.info("Filter disabled")
    else:
        await message.answer("Please use /filter Yes or /filter No to enable or disable the filter.")
        logger.info("Invalid /filter input")

# Handler for messages (acting as /button and /filter logic)
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

    # Extract CA from the message
    ca = None
    text = message.text
    if message.entities:
        for entity in message.entities:
            if entity.type in ["url", "text_link"]:
                url = entity.url if entity.type == "text_link" else text[entity.offset:entity.offset + entity.length]
                logger.info(f"Found URL: {url}")
                ca_match = re.search(r'[A-Za-z0-9]{44}', url)
                if ca_match:
                    ca = ca_match.group(0)
                    logger.info(f"Extracted CA: {ca}")
                break

    # Check for BuyPercent and SellPercent
    has_buy_sell = False
    lines = [line.strip() for line in text.replace('\r\n', '\n').split('\n') if line.strip()]
    for line in lines:
        if "├Sum 🅑:" in line and "Sum 🅢:" in line:
            match = re.search(r'├Sum 🅑:(\d+\.?\d*)%\s*\|\s*Sum 🅢:(\d+\.?\d*)%', line)
            if match:
                has_buy_sell = True
                logger.info(f"Found BuyPercent and SellPercent: {match.group(0)}")
                break

    # If BuyPercent/SellPercent exists and filter is enabled, produce /filter output
    if has_buy_sell and filter_enabled:
        logger.info("Message contains BuyPercent/SellPercent and filter is enabled, producing /filter output")
        output_text = (
            "Filter Passed:\n"
            "New Durham Bulls Mascot (Champ)\n"
            "CA: EABqeDRLv6B2iGzdytnjBaifHDqyEu5XZonGoqDupump"
        )
        # Apply code entity to the CA
        entities = []
        text_before_ca = "Filter Passed:\nNew Durham Bulls Mascot (Champ)\nCA: "
        ca_new_offset = len(text_before_ca.encode('utf-16-le')) // 2  # UTF-16 offset
        ca_length = 44  # Hardcode length since CA is always 44 characters
        text_length_utf16 = len(output_text.encode('utf-16-le')) // 2
        if ca_new_offset >= 0 and ca_new_offset + ca_length <= text_length_utf16:
            entities.append(MessageEntity(type="code", offset=ca_new_offset, length=ca_length))
            logger.info(f"Applied code entity: Offset {ca_new_offset}, Length {ca_length}")
        else:
            logger.warning(f"Skipping invalid code entity: Offset {ca_new_offset}, Length {ca_length}")

        try:
            logger.info("Attempting to edit the original message with /filter output")
            edited_message = await message.edit_text(output_text, entities=entities)
            logger.info(f"Successfully edited message ID: {edited_message.message_id}")
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            logger.info("Falling back to posting a new message without deleting the original")
            new_message = await message.answer(output_text, entities=entities)
            logger.info(f"New message ID: {new_message.message_id}")
        return  # Skip /button functionality

    # Default /button functionality if no BuyPercent/SellPercent or filter is disabled
    if ca:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Bloom", url=f"https://t.me/BloomSolana_bot?start=ref_humbleguy_ca_{ca}"),
                InlineKeyboardButton(text="Fasol", url=f"https://t.me/fasol_robot?start=ref_humbleguy_ca_{ca}"),
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
                lines[i] = f"🔗 CA: {ca}"
                break
        text = "\n".join(line.strip() for line in lines if line.strip())
        logger.info(f"Final text to send: {text}")

        # Apply the code entity to the CA only (excluding the emoji and "CA: ")
        entities = []
        text_before_ca = text[:text.find(ca)]
        ca_new_offset = len(text_before_ca.encode('utf-16-le')) // 2  # UTF-16 offset
        logger.info(f"CA position in final text: {text.find(ca)}")
        logger.info(f"Text before CA: {text_before_ca}")
        logger.info(f"Calculated CA UTF-16 offset: {ca_new_offset}")
        if ca_new_offset >= 0:
            ca_length = 44
            text_length_utf16 = len(text.encode('utf-16-le')) // 2
            if ca_new_offset + ca_length <= text_length_utf16:
                entities.append(MessageEntity(type="code", offset=ca_new_offset, length=ca_length))
                logger.info(f"Applied code entity: Offset {ca_new_offset}, Length {ca_length}")
            else:
                logger.warning(f"Skipping invalid code entity: Offset {ca_new_offset}, Length {ca_length}")

        try:
            logger.info("Attempting to edit the original message")
            edited_message = await message.edit_text(text, reply_markup=keyboard, entities=entities)
            logger.info(f"Successfully edited message ID: {edited_message.message_id}")
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            logger.info("Falling back to posting a new message without deleting the original")
            new_message = await message.answer(text, reply_markup=keyboard, entities=entities)
            logger.info(f"New message ID: {new_message.message_id}")
    else:
        logger.info("No CA found in URL")

async def main():
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

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

# Define the specific chat ID or username where "Filter" can be toggled
FILTER_CHAT_ID = 123456789  # Replace with the actual chat ID or username (e.g., "@FilterChannel")

# In-memory storage for SETUP_VAL and FILTER state per chat
setup_vals = {}  # {chat_id: value}
filter_states = {}  # {chat_id: "Yes" or "No"}

@app.route('/')
def home():
    logger.info("Flask route '/' accessed")
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

# Buttons function (original functionality)
async def process_buttons(message: types.Message, text: str, ca: str):
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
    # Clean the text
    text = re.sub(r'Forwarded from .*\n', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Buy token on Fasol Reflink', '', text, flags=re.IGNORECASE)
    # Format the CA line
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if ca in line:
            lines[i] = f"🔗 CA: {ca}"
            break
    text = "\n".join(line.strip() for line in lines if line.strip())
    logger.info(f"Final text for Buttons: {text}")

    # Apply code entity to the CA
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
        logger.info("Attempting to edit the original message for Buttons")
        edited_message = await message.edit_text(text, reply_markup=keyboard, entities=entities)
        logger.info(f"Successfully edited message ID for Buttons: {edited_message.message_id}")
    except Exception as e:
        logger.error(f"Error editing message for Buttons: {e}")
        logger.info("Editing failed, skipping to avoid duplicates")

# Filter function (new message creation)
async def process_filter(message: types.Message, text: str, ca: str):
    logger.info("Processing Filter function")
    # Extract BuyPercent and SellPercent
    buy_percent = None
    sell_percent = None
    for line in text.splitlines():
        if "├Sum 🅑:" in line and "Sum 🅢:" in line:
            match = re.search(r'├Sum 🅑:(\d+\.?\d*)% \| Sum 🅢:(\d+\.?\d*)%', line)
            if match:
                buy_percent = float(match.group(1))
                sell_percent = float(match.group(2))
                logger.info(f"Extracted BuyPercent: {buy_percent}, SellPercent: {sell_percent}")
                break

    # Calculate BSRatio
    if buy_percent is not None and sell_percent is not None and sell_percent != 0:  # Avoid division by zero
        bs_ratio = buy_percent / sell_percent
        logger.info(f"Calculated BSRatio: {bs_ratio}")
        # Get the chat-specific SETUP_VAL, default to 1.0 if not set
        chat_id = str(message.chat.id)
        setup_val = setup_vals.get(chat_id, 1.0)
        logger.info(f"Using SETUP_VAL for chat {chat_id}: {setup_val}")
        # Compare BSRatio with SetupVal
        if bs_ratio >= setup_val:
            logger.info(f"BSRatio ({bs_ratio}) >= SetupVal ({setup_val}), preparing Filter output")
            # Get the first two lines of the original message
            lines = text.splitlines()
            first_line = "Filter Passed"
            second_line = lines[1].strip() if len(lines) > 1 else ""  # Handle cases with fewer than 2 lines
            # Prepare the output text
            output_text = f"{first_line}\n{second_line}\nCA: {ca}"
            logger.info(f"Filter output text: {output_text}")

            # Apply code entity to the CA
            entities = []
            text_before_ca = f"{first_line}\n{second_line}\nCA: "
            ca_new_offset = len(text_before_ca.encode('utf-16-le')) // 2  # UTF-16 offset
            logger.info(f"CA position in final text: {len(text_before_ca)}")
            logger.info(f"Text before CA: {text_before_ca}")
            logger.info(f"Calculated CA UTF-16 offset: {ca_new_offset}")
            if ca_new_offset >= 0:
                ca_length = 44
                text_length_utf16 = len(output_text.encode('utf-16-le')) // 2
                if ca_new_offset + ca_length <= text_length_utf16:
                    entities.append(MessageEntity(type="code", offset=ca_new_offset, length=ca_length))
                    logger.info(f"Applied code entity: Offset {ca_new_offset}, Length {ca_length}")
                else:
                    logger.warning(f"Skipping invalid code entity: Offset {ca_new_offset}, Length {ca_length}")

            try:
                logger.info("Creating new message for Filter output")
                await message.answer(output_text, entities=entities)
                logger.info("Successfully created new message for Filter")
            except Exception as e:
                logger.error(f"Error creating new message for Filter: {e}")
        else:
            logger.info(f"BSRatio ({bs_ratio}) < SetupVal ({setup_val}), doing nothing")
    else:
        logger.info("Could not calculate BSRatio, doing nothing")

# Command handlers
@dp.message(F.text.startswith('/setupval'))
async def set_setup_val(message: types.Message):
    chat_id = str(message.chat.id)
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("Usage: /setupval <value> (e.g., /setupval 1.2)")
        return
    try:
        value = float(parts[1])
        if value <= 0:
            await message.reply("Value must be positive.")
            return
        setup_vals[chat_id] = value
        logger.info(f"Set SETUP_VAL to {value} for chat {chat_id}")
        await message.reply(f"SETUP_VAL set to {value} for this chat.")
    except ValueError:
        await message.reply("Invalid value. Please enter a number (e.g., 1.2).")

@dp.message(F.text.startswith('/filter'))
async def toggle_filter(message: types.Message):
    chat_id = str(message.chat.id)
    parts = message.text.split()
    if len(parts) != 2 or parts[1].lower() not in ["yes", "no"]:
        await message.reply("Usage: /filter Yes or /filter No")
        return
    state = parts[1].lower()
    filter_states[chat_id] = state
    logger.info(f"Set Filter state to {state} for chat {chat_id}")
    await message.reply(f"Filter toggled to {state} for this chat.")

@dp.message(F.text)
@dp.channel_post(F.text)
async def handle_message(message: types.Message):
    logger.info(f"Received message: {message.text}")
    logger.info(f"Chat type: {message.chat.type}")
    logger.info(f"Original message ID: {message.message_id}")
    logger.info(f"Forwarded from: {message.forward_from_chat}")
    logger.info(f"Entities: {message.entities}")
    logger.info(f"Chat ID: {message.chat.id}")

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
            chat_id = str(message.chat.id)
            # Check if the message is from the specific chat for Filter
            if chat_id == str(FILTER_CHAT_ID) or (hasattr(message.chat, 'username') and message.chat.username == FILTER_CHAT_ID):
                logger.info(f"Checking Filter state for chat {chat_id}")
                filter_state = filter_states.get(chat_id, "No").lower()
                if filter_state == "yes":
                    logger.info(f"Activating Filter function in chat {chat_id}")
                    await process_filter(message, text, ca)
                else:
                    logger.info(f"Filter is off, activating Buttons function in chat {chat_id}")
                    await process_buttons(message, text, ca)
            else:
                logger.info(f"Activating Buttons function in chat {chat_id}")
                await process_buttons(message, text, ca)
        else:
            logger.info("No CA found in URL")

async def main():
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

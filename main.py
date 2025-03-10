from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from aiogram.filters import Command
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

# Global variables
filter_enabled = False
PassValue = None  # Initialize PassValue as None

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
@dp.message(Command(commands=["filter"]))
async def toggle_filter(message: types.Message):
    global filter_enabled
    text = message.text.lower().replace('/filter', '').strip()
    logger.info(f"Received /filter command with text: {text}")

    if text == "yes":
        filter_enabled = True
        await message.answer("Filter set to: Yes ✅")
        logger.info("Sent response: Filter set to: Yes ✅")
        logger.info("Filter enabled")
    elif text == "no":
        filter_enabled = False
        await message.answer("Filter set to: No 🚫")
        logger.info("Sent response: Filter set to: No 🚫")
        logger.info("Filter disabled")
    else:
        await message.answer("Please specify Yes or No after /filter (e.g., /filter Yes) 🤔")
        logger.info("Sent response: Please specify Yes or No after /filter (e.g., /filter Yes) 🤔")
        logger.info("Invalid /filter input or no value provided")

# Handler for /setupval command to set PassValue
@dp.message(Command(commands=["setupval"]))
async def setup_val(message: types.Message):
    global PassValue
    text = message.text.lower().replace('/setupval', '').strip()
    logger.info(f"Received /setupval command with text: {text}")

    try:
        # Attempt to convert the input to a float
        value = float(text)
        PassValue = value
        await message.answer(f"PassValue set to: {PassValue} ✅")
        logger.info(f"Sent response: PassValue set to: {PassValue} ✅")
        logger.info(f"PassValue updated to: {PassValue}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /setupval 1.2) 🚫")
        logger.info("Sent response: Please provide a valid numerical value (e.g., /setupval 1.2) 🚫")
        logger.info("Invalid /setupval input: not a number")

# Handler for messages (acting as /button and /filter logic)
@dp.message(F.text)
@dp.channel_post(F.text)
async def convert_link_to_button(message: types.Message):
    logger.info(f"Received full message text: {message.text}")  # Log full text for debugging
    logger.info(f"Chat type: {message.chat.type}")
    logger.info(f"Original message ID: {message.message_id}")
    logger.info(f"Forwarded from: {message.forward_from_chat}")
    logger.info(f"Entities: {message.entities}")
    logger.info(f"Filter enabled state: {filter_enabled}")  # Debug filter state
    logger.info(f"Current PassValue: {PassValue}")  # Debug PassValue

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
    buy_percent = None
    sell_percent = None
    lines = [line.strip() for line in text.replace('\r\n', '\n').split('\n') if line.strip()]
    logger.info(f"Lines to check for Buy/Sell percent: {lines}")  # Debug all lines
    for line in lines:
        logger.info(f"Checking line: '{line}'")  # Debug each line
        # Flexible regex to handle variations in whitespace or formatting
        match = re.search(r'├?Sum\s*🅑:\s*(\d+\.?\d*)%\s*[\|]\s*Sum\s*🅢:\s*(\d+\.?\d*)%', line)
        if match:
            has_buy_sell = True
            buy_percent = float(match.group(1))
            sell_percent = float(match.group(2))
            logger.info(f"Found BuyPercent and SellPercent: {match.group(0)} with groups: {match.groups()}")
            break
        else:
            logger.warning(f"No match for regex on line: '{line}'")  # Debug regex failure

    # If BuyPercent/SellPercent exists, calculate BSRatio and compare with PassValue
    if has_buy_sell:
        logger.info("Message contains BuyPercent/SellPercent, processing BSRatio")
        # Use the first two lines of the source message
        if len(lines) >= 2:
            first_line = lines[0]
            second_line = lines[1]
            logger.info(f"Using first line: '{first_line}'")
            logger.info(f"Using second line: '{second_line}'")
        else:
            logger.warning("Source message has fewer than 2 lines, using defaults")
            first_line = "Unknown Token"
            second_line = "🔗 CA: UnknownCA"

        # Calculate BSRatio
        try:
            if sell_percent == 0:
                logger.warning("SellPercent is 0, cannot calculate BSRatio, assuming infinity")
                bs_ratio = float('inf')  # Handle division by zero
            else:
                bs_ratio = buy_percent / sell_percent
                logger.info(f"Calculated BSRatio: {buy_percent} / {sell_percent} = {bs_ratio}")
        except Exception as e:
            logger.error(f"Error calculating BSRatio: {e}")
            bs_ratio = 0  # Fallback in case of error

        # Compare BSRatio with PassValue
        if PassValue is None:
            logger.warning("PassValue is not set, cannot compare BSRatio")
            await message.answer("⚠️ Please set PassValue using /setupval (e.g., /setupval 1.2) before filtering.")
            return

        if bs_ratio >= PassValue:
            logger.info(f"BSRatio ({bs_ratio}) >= PassValue ({PassValue}), producing /filter output")
            output_text = f"Filter Passed: 🎉\n{first_line}\n{second_line}"
        else:
            logger.info(f"BSRatio ({bs_ratio}) < PassValue ({PassValue}), CA did not qualify")
            output_text = f"CA did not qualify: 🚫 BSRatio {bs_ratio:.2f}"

        # Apply code entity to the CA in the output (if present)
        entities = []
        ca_match = re.search(r'[A-Za-z0-9]{44}', output_text)
        if ca_match:
            ca = ca_match.group(0)
            text_before_ca = output_text[:output_text.find(ca)]
            ca_new_offset = len(text_before_ca.encode('utf-16-le')) // 2  # UTF-16 offset
            ca_length = 44
            text_length_utf16 = len(output_text.encode('utf-16-le')) // 2
            if ca_new_offset >= 0 and ca_new_offset + ca_length <= text_length_utf16:
                entities.append(MessageEntity(type="code", offset=ca_new_offset, length=ca_length))
                logger.info(f"Applied code entity: Offset {ca_new_offset}, Length {ca_length}")
            else:
                logger.warning(f"Skipping invalid code entity: Offset {ca_new_offset}, Length {ca_length}")
        else:
            logger.warning("No CA found in output for code entity")

        try:
            logger.info("Creating new message for output")
            new_message = await message.answer(output_text, entities=entities)
            logger.info(f"New message ID: {new_message.message_id}")
        except Exception as e:
            logger.error(f"Error creating new message: {e}")
        return  # Skip all further processing, including /button

    # Default /button functionality if no BuyPercent/SellPercent
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
            logger.info("Falling back to posting a new message")
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

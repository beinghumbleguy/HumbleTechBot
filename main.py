from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, BotCommand
from aiogram.filters import Command
import asyncio
import logging
import os
import re
from flask import Flask
from threading import Thread
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
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
RangeLow = None   # Initialize RangeLow as None
authorized_users = ["@BeingHumbleGuy"]  # List of authorized users, starting with the super user
additional_user_added = False  # Flag to track if the additional user has been added

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

# Function to check if the user is authorized
def is_authorized(username: str) -> bool:
    return username in authorized_users

# Web scraping function to get token data (without proxy)
def get_gmgn_token_data(mint_address):
    url = f"https://gmgn.ai/sol/token/{mint_address}"
    headers = {"User-Agent": "Mozilla/5.0"}  # Prevents basic bot blocking

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            try:
                # Extract Market Cap
                market_cap = soup.find("div", text="Market Cap").find_next_sibling("div").text.strip()

                # Extract Liquidity
                liquidity = soup.find("div", text="Liquidity").find_next_sibling("div").text.strip()

                # Extract Price
                price = soup.find("div", text="Price").find_next_sibling("div").text.strip()

                return {
                    "market_cap": market_cap,
                    "liquidity": liquidity,
                    "price": price,
                    "contract": mint_address
                }
            except AttributeError:
                return {"error": "Failed to extract data. Structure may have changed."}
        else:
            return {"error": f"Request failed with status {response.status_code}"}
    except requests.RequestException as e:
        return {"error": f"Network error: {str(e)}"}

# Handler for /adduser command to add an authorized user (only for super user)
@dp.message(Command(commands=["adduser"]))
async def add_user(message: types.Message):
    global additional_user_added
    username = message.from_user.username
    logger.info(f"Received /adduser command from user: @{username}")

    # Check if the user is the super user
    if username != "BeingHumbleGuy":
        await message.answer("⚠️ Only @BeingHumbleGuy can add authorized users.")
        logger.info(f"Unauthorized /adduser attempt by @{username}")
        return

    # Check if an additional user has already been added
    if additional_user_added:
        await message.answer("⚠️ An additional user has already been added. Only one additional user is allowed.")
        logger.info("Additional user already added, rejecting new addition")
        return

    # Extract the new username from the command
    text = message.text.lower().replace('/adduser', '').strip()
    if not text:
        await message.answer("Please provide a username to add (e.g., /adduser @NewUser) 🤔")
        logger.info("No username provided for /adduser")
        return

    # Ensure the username starts with @
    new_user = text if text.startswith('@') else f"@{text}"
    if new_user == "@BeingHumbleGuy":
        await message.answer("⚠️ @BeingHumbleGuy is already the super user.")
        logger.info("Attempt to add @BeingHumbleGuy, already a super user")
        return

    # Add the new user to the authorized list
    authorized_users.append(new_user)
    additional_user_added = True
    await message.answer(f"Authorized user added: {new_user} ✅")
    logger.info(f"Authorized user added: {new_user}, Authorized users: {authorized_users}")

# Handler for /filter command to enable/disable filter
@dp.message(Command(commands=["filter"]))
async def toggle_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /filter command from user: @{username}")

    # Check if the user is authorized
    if not is_authorized(f"@{username}"):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /filter attempt by @{username}")
        return

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
    username = message.from_user.username
    logger.info(f"Received /setupval command from user: @{username}")

    # Check if the user is authorized
    if not is_authorized(f"@{username}"):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setupval attempt by @{username}")
        return

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

# Handler for /setrangelow command to set RangeLow
@dp.message(Command(commands=["setrangelow"]))
async def set_range_low(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setrangelow command from user: @{username}")

    # Check if the user is authorized
    if not is_authorized(f"@{username}"):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setrangelow attempt by @{username}")
        return

    global RangeLow
    text = message.text.lower().replace('/setrangelow', '').strip()
    logger.info(f"Received /setrangelow command with text: {text}")

    try:
        # Attempt to convert the input to a float
        value = float(text)
        RangeLow = value
        await message.answer(f"RangeLow set to: {RangeLow} ✅")
        logger.info(f"Sent response: RangeLow set to: {RangeLow} ✅")
        logger.info(f"RangeLow updated to: {RangeLow}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /setrangelow 1.1) 🚫")
        logger.info("Sent response: Please provide a valid numerical value (e.g., /setrangelow 1.1) 🚫")
        logger.info("Invalid /setrangelow input: not a number")

# Handler for messages (acting as /button and /filter logic)
@dp.message(F.text)
@dp.channel_post(F.text)
async def convert_link_to_button(message: types.Message):
    # Skip if the message is a command (starts with /)
    if message.text.startswith('/'):
        logger.info(f"Skipping command message: {message.text}")
        return

    logger.info(f"Received full message text: {message.text}")  # Log full text for debugging
    logger.info(f"Chat type: {message.chat.type}")
    logger.info(f"Original message ID: {message.message_id}")
    logger.info(f"Forwarded from: {message.forward_from_chat}")
    logger.info(f"Entities: {message.entities}")
    logger.info(f"Filter enabled state: {filter_enabled}")  # Debug filter state
    logger.info(f"Current PassValue: {PassValue}")  # Debug PassValue
    logger.info(f"Current RangeLow: {RangeLow}")  # Debug RangeLow

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

    # If BuyPercent/SellPercent exists, calculate BSRatio and compare with PassValue and RangeLow
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

        # Check if PassValue and RangeLow are set
        if PassValue is None or RangeLow is None:
            logger.warning("PassValue or RangeLow is not set, cannot compare BSRatio")
            missing_vars = []
            if PassValue is None:
                missing_vars.append("PassValue")
            if RangeLow is None:
                missing_vars.append("RangeLow")
            await message.answer(f"⚠️ Please set {', '.join(missing_vars)} using /setupval and /setrangelow before filtering.")
            return

        # Check filter conditions: BSRatio >= PassValue OR (1 <= BSRatio <= RangeLow)
        if bs_ratio >= PassValue or (1 <= bs_ratio <= RangeLow):
            logger.info(f"Filter passed - BSRatio: {bs_ratio}, PassValue: {PassValue}, RangeLow: {RangeLow}")
            logger.info(f"Condition met: BSRatio >= PassValue: {bs_ratio >= PassValue}, or 1 <= BSRatio <= RangeLow: {1 <= bs_ratio <= RangeLow}")
            output_text = f"Filter Passed: 🎉 BSRatio {bs_ratio:.2f}\n{first_line}\n{second_line}"
        else:
            logger.info(f"Filter failed - BSRatio: {bs_ratio}, PassValue: {PassValue}, RangeLow: {RangeLow}")
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
    if ca and "reflink" in message.text.lower():  # Only add buttons if "reflink" is present
        logger.info(f"Adding buttons because 'reflink' found in message: {message.text}")
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
        logger.info("No CA found in URL or 'reflink' not present, skipping button addition")

# New handler for \ca <token_ca> command
@dp.message(commands=["ca"])
async def cmd_ca(message: types.Message):
    logger.info(f"Received \ca command from {message.from_user.username}")
    if not is_authorized(message.from_user.username):
        await message.answer("You are not authorized to use this command.")
        return

    # Extract token CA from message
    text = message.text
    parts = text.split()
    if len(parts) != 2:
        await message.answer("Usage: \\ca <token_ca>")
        return

    token_ca = parts[1].strip()
    logger.info(f"Processing token CA: {token_ca}")

    # Get token data
    token_data = get_gmgn_token_data(token_ca)
    if "error" in token_data:
        await message.reply(f"Error: {token_data['error']}")
    else:
        response = (
            f"Token Data for CA: {token_data['contract']}\n"
            f"📈 Market Cap: {token_data['market_cap']}\n"
            f"💧 Liquidity: {token_data['liquidity']}\n"
            f"💰 Price: {token_data['price']}"
        )
        await message.reply(response)

async def main():
    # Define the commands with descriptions
    commands = [
        BotCommand(command="filter", description="Enable or disable the filter (Yes/No)"),
        BotCommand(command="setupval", description="Set the PassValue for filtering (e.g., /setupval 1.2)"),
        BotCommand(command="setrangelow", description="Set the RangeLow for filtering (e.g., /setrangelow 1.1)"),
        BotCommand(command="adduser", description="Add an authorized user (only for @BeingHumbleGuy)"),
        BotCommand(command="ca", description="Get token data (e.g., \\ca <token_ca>)")
    ]
    
    # Set the bot commands
    try:
        await bot.set_my_commands(commands)
        logger.info("Successfully set bot commands for suggestions")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, BotCommand
from aiogram.filters import Command
import asyncio
import logging
import os
import re
from flask import Flask, send_file, request, abort
from threading import Thread
import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import threading
import secrets

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
dp = Dispatcher()  # Define dp here, before any @dp.message decorators
app = Flask(__name__)

# Thread lock for safe CSV writing
csv_lock = threading.Lock()

# Global variables
filter_enabled = False
PassValue = None
RangeLow = None
authorized_users = ["@BeingHumbleGuy"]
additional_user_added = False

# BSRatio filter toggles
CheckHighEnabled = False
CheckLowEnabled = False

# New filter thresholds
DevSoldThreshold = None  # "Yes" or "No"
DevSoldLeft = None  # Numerical percentage (e.g., 10 for 10%)
Top10Threshold = None
SnipersThreshold = None
BundlesThreshold = None
InsidersThreshold = None
KOLsThreshold = None

# New filter toggles
DevSoldFilterEnabled = False
Top10FilterEnabled = False
SniphersFilterEnabled = False
BundlesFilterEnabled = False
InsidersFilterEnabled = False
KOLsFilterEnabled = False

# CSV file path
CSV_FILE = "ca_filter_log.csv"

# Secret token for securing the Flask download route
DOWNLOAD_TOKEN = secrets.token_urlsafe(32)
logger.info(f"Generated download token: {DOWNLOAD_TOKEN}")

# Initialize CSV file with headers if it doesn't exist
def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "CA", "BSRatio", "BSRatio_Pass", "BSRatio_Low_Pass",
                "DevSold", "DevSoldLeftValue", "DevSold_Pass", "Top10", "Top10_Pass",
                "Snipers", "Snipers_Pass", "Bundles", "Bundles_Pass", "Insiders", "Insiders_Pass",
                "KOLs", "KOLs_Pass", "Overall_Pass"
            ])
        logger.info(f"Created CSV file: {CSV_FILE}")

# Log filter results to CSV
def log_to_csv(ca, bs_ratio, bs_ratio_pass, check_low_pass, dev_sold, dev_sold_left_value, dev_sold_pass,
               top_10, top_10_pass, snipers, snipers_pass, bundles, bundles_pass,
               insiders, insiders_pass, kols, kols_pass, overall_pass):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with csv_lock:
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, ca if ca else "N/A",
                bs_ratio if bs_ratio is not None else "N/A",
                bs_ratio_pass if (CheckHighEnabled or CheckLowEnabled) else "N/A",
                check_low_pass if CheckLowEnabled else "N/A",
                dev_sold if dev_sold is not None else "N/A",
                dev_sold_left_value if dev_sold_left_value is not None else "N/A",
                dev_sold_pass if DevSoldFilterEnabled and dev_sold is not None else "N/A",
                top_10 if top_10 is not None else "N/A",
                top_10_pass if Top10FilterEnabled and top_10 is not None else "N/A",
                snipers if snipers is not None else "N/A",
                snipers_pass if SniphersFilterEnabled and snipers is not None else "N/A",
                bundles if bundles is not None else "N/A",
                bundles_pass if BundlesFilterEnabled and bundles is not None else "N/A",
                insiders if insiders is not None else "N/A",
                insiders_pass if InsidersFilterEnabled and insiders is not None else "N/A",
                kols if kols is not None else "N/A",
                kols_pass if KOLsFilterEnabled and kols is not None else "N/A",
                overall_pass
            ])
    logger.info(f"Logged filter results to CSV for CA: {ca}")

# Flask routes
@app.route('/')
def home():
    logger.info("Flask route '/' accessed")
    return "Bot is running!"

@app.route('/download/csv')
def download_csv():
    token = request.args.get('token')
    if token != DOWNLOAD_TOKEN:
        logger.warning("Unauthorized attempt to access /download/csv")
        abort(403)  # Forbidden
    if not os.path.exists(CSV_FILE):
        logger.warning("CSV file not found for download")
        return "CSV file not found.", 404
    logger.info("Serving CSV file for download")
    return send_file(CSV_FILE, as_attachment=True, download_name="ca_filter_log.csv")

# Function to run Flask app in a separate thread
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

# Function to check if the user is authorized
def is_authorized(username: str) -> bool:
    if not username.startswith('@'):
        username = f"@{username}"
    return username in authorized_users

# Web scraping function to get token data (without proxy)
def get_gmgn_token_data(mint_address):
    url = f"https://gmgn.ai/sol/token/{mint_address}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            try:
                market_cap = soup.find("div", text="Market Cap").find_next_sibling("div").text.strip()
                liquidity = soup.find("div", text="Liquidity").find_next_sibling("div").text.strip()
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

    if username != "BeingHumbleGuy":
        await message.answer("⚠️ Only @BeingHumbleGuy can add authorized users.")
        logger.info(f"Unauthorized /adduser attempt by @{username}")
        return

    if additional_user_added:
        await message.answer("⚠️ An additional user has already been added. Only one additional user is allowed.")
        logger.info("Additional user already added, rejecting new addition")
        return

    text = message.text.lower().replace('/adduser', '').strip()
    if not text:
        await message.answer("Please provide a username to add (e.g., /adduser @NewUser) 🤔")
        logger.info("No username provided for /adduser")
        return

    new_user = text if text.startswith('@') else f"@{text}"
    if new_user == "@BeingHumbleGuy":
        await message.answer("⚠️ @BeingHumbleGuy is already the super user.")
        logger.info("Attempt to add @BeingHumbleGuy, already a super user")
        return

    authorized_users.append(new_user)
    additional_user_added = True
    await message.answer(f"Authorized user added: {new_user} ✅")
    logger.info(f"Authorized user added: {new_user}, Authorized users: {authorized_users}")

# Handler for /filter command to enable/disable filter
@dp.message(Command(commands=["filter"]))
async def toggle_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /filter command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /filter attempt by @{username}")
        return

    global filter_enabled
    text = message.text.lower().replace('/filter', '').strip()
    logger.info(f"Received /filter command with text: {text}")

    if text == "yes":
        filter_enabled = True
        await message.answer("Filter set to: Yes ✅")
        logger.info("Filter enabled")
    elif text == "no":
        filter_enabled = False
        await message.answer("Filter set to: No 🚫")
        logger.info("Filter disabled")
    else:
        await message.answer("Please specify Yes or No after /filter (e.g., /filter Yes) 🤔")
        logger.info("Invalid /filter input")

# Handler for /checkhigh command to enable/disable CheckHigh filter
@dp.message(Command(commands=["checkhigh"]))
async def toggle_checkhigh(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /checkhigh command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /checkhigh attempt by @{username}")
        return

    global CheckHighEnabled
    text = message.text.lower().replace('/checkhigh', '').strip()
    logger.info(f"Received /checkhigh command with text: {text}")

    if text == "yes":
        CheckHighEnabled = True
        await message.answer("CheckHigh filter set to: Yes ✅")
        logger.info("CheckHigh filter enabled")
    elif text == "no":
        CheckHighEnabled = False
        await message.answer("CheckHigh filter set to: No 🚫")
        logger.info("CheckHigh filter disabled")
    else:
        await message.answer("Please specify Yes or No after /checkhigh (e.g., /checkhigh Yes) 🤔")
        logger.info("Invalid /checkhigh input")

# Handler for /checklow command to enable/disable CheckLow filter
@dp.message(Command(commands=["checklow"]))
async def toggle_checklow(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /checklow command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /checklow attempt by @{username}")
        return

    global CheckLowEnabled
    text = message.text.lower().replace('/checklow', '').strip()
    logger.info(f"Received /checklow command with text: {text}")

    if text == "yes":
        CheckLowEnabled = True
        await message.answer("CheckLow filter set to: Yes ✅")
        logger.info("CheckLow filter enabled")
    elif text == "no":
        CheckLowEnabled = False
        await message.answer("CheckLow filter set to: No 🚫")
        logger.info("CheckLow filter disabled")
    else:
        await message.answer("Please specify Yes or No after /checklow (e.g., /checklow Yes) 🤔")
        logger.info("Invalid /checklow input")

# Handler for /setupval command to set PassValue (for CheckHigh)
@dp.message(Command(commands=["setupval"]))
async def setup_val(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setupval command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setupval attempt by @{username}")
        return

    global PassValue
    text = message.text.lower().replace('/setupval', '').strip()
    logger.info(f"Received /setupval command with text: {text}")

    try:
        value = float(text)
        PassValue = value
        await message.answer(f"PassValue set to: {PassValue} ✅")
        logger.info(f"PassValue updated to: {PassValue}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /setupval 1.2) 🚫")
        logger.info("Invalid /setupval input: not a number")

# Handler for /setrangelow command to set RangeLow (for CheckLow)
@dp.message(Command(commands=["setrangelow"]))
async def set_range_low(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setrangelow command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setrangelow attempt by @{username}")
        return

    global RangeLow
    text = message.text.lower().replace('/setrangelow', '').strip()
    logger.info(f"Received /setrangelow command with text: {text}")

    try:
        value = float(text)
        RangeLow = value
        await message.answer(f"RangeLow set to: {RangeLow} ✅")
        logger.info(f"RangeLow updated to: {RangeLow}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /setrangelow 1.1) 🚫")
        logger.info("Invalid /setrangelow input: not a number")

# Handler for /setdevsold command (Yes/No)
@dp.message(Command(commands=["setdevsold"]))
async def set_devsold(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setdevsold command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        return

    global DevSoldThreshold
    text = message.text.lower().replace('/setdevsold', '').strip()
    if text in ["yes", "no"]:
        DevSoldThreshold = text
        await message.answer(f"DevSoldThreshold set to: {DevSoldThreshold} ✅")
        logger.info(f"DevSoldThreshold updated to: {DevSoldThreshold}")
    else:
        await message.answer("Please specify Yes or No (e.g., /setdevsold Yes) 🚫")

# Handler for /setdevsoldleft command (numerical percentage)
@dp.message(Command(commands=["setdevsoldleft"]))
async def set_devsoldleft(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setdevsoldleft command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        return

    global DevSoldLeft
    text = message.text.lower().replace('/setdevsoldleft', '').strip()
    try:
        value = float(text)
        if value < 0 or value > 100:
            await message.answer("Please provide a percentage between 0 and 100 (e.g., /setdevsoldleft 10) 🚫")
            return
        DevSoldLeft = value
        await message.answer(f"DevSoldLeft threshold set to: {DevSoldLeft}% ✅")
        logger.info(f"DevSoldLeft updated to: {DevSoldLeft}")
    except ValueError:
        await message.answer("Please provide a valid numerical percentage (e.g., /setdevsoldleft 10) 🚫")

# Handler for /devsoldfilter command
@dp.message(Command(commands=["devsoldfilter"]))
async def toggle_devsold_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /devsoldfilter command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        return

    global DevSoldFilterEnabled
    text = message.text.lower().replace('/devsoldfilter', '').strip()
    if text == "yes":
        DevSoldFilterEnabled = True
        await message.answer("DevSold filter set to: Yes ✅")
        logger.info("DevSold filter enabled")
    elif text == "no":
        DevSoldFilterEnabled = False
        await message.answer("DevSold filter set to: No 🚫")
        logger.info("DevSold filter disabled")
    else:
        await message.answer("Please specify Yes or No after /devsoldfilter (e.g., /devsoldfilter Yes) 🤔")

# Top10
@dp.message(Command(commands=["settop10"]))
async def set_top10(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /settop10 command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        return

    global Top10Threshold
    text = message.text.lower().replace('/settop10', '').strip()
    try:
        value = float(text)
        Top10Threshold = value
        await message.answer(f"Top10Threshold set to: {Top10Threshold} ✅")
        logger.info(f"Top10Threshold updated to: {Top10Threshold}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /settop10 20) 🚫")

@dp.message(Command(commands=["top10filter"]))
async def toggle_top10_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /top10filter command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        return

    global Top10FilterEnabled
    text = message.text.lower().replace('/top10filter', '').strip()
    if text == "yes":
        Top10FilterEnabled = True
        await message.answer("Top10 filter set to: Yes ✅")
        logger.info("Top10 filter enabled")
    elif text == "no":
        Top10FilterEnabled = False
        await message.answer("Top10 filter set to: No 🚫")
        logger.info("Top10 filter disabled")
    else:
        await message.answer("Please specify Yes or No after /top10filter (e.g., /top10filter Yes) 🤔")

# Snipers
@dp.message(Command(commands=["setsnipers"]))
async def set_snipers(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setsnipers command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        return

    global SnipersThreshold
    text = message.text.lower().replace('/setsnipers', '').strip()
    try:
        value = float(text)
        SnipersThreshold = value
        await message.answer(f"SnipersThreshold set to: {SnipersThreshold} ✅")
        logger.info(f"SnipersThreshold updated to: {SnipersThreshold}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /setsnipers 3) 🚫")

@dp.message(Command(commands=["snipersfilter"]))
async def toggle_snipers_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /snipersfilter command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        return

    global SniphersFilterEnabled
    text = message.text.lower().replace('/snipersfilter', '').strip()
    if text == "yes":
        SniphersFilterEnabled = True
        await message.answer("Snipers filter set to: Yes ✅")
        logger.info("Snipers filter enabled")
    elif text == "no":
        SniphersFilterEnabled = False
        await message.answer("Snipers filter set to: No 🚫")
        logger.info("Snipers filter disabled")
    else:
        await message.answer("Please specify Yes or No after /snipersfilter (e.g., /snipersfilter Yes) 🤔")

# Bundles
@dp.message(Command(commands=["setbundles"]))
async def set_bundles(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setbundles command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        return

    global BundlesThreshold
    text = message.text.lower().replace('/setbundles', '').strip()
    try:
        value = float(text)
        BundlesThreshold = value
        await message.answer(f"BundlesThreshold set to: {BundlesThreshold} ✅")
        logger.info(f"BundlesThreshold updated to: {BundlesThreshold}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /setbundles 1) 🚫")

@dp.message(Command(commands=["bundlesfilter"]))
async def toggle_bundles_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /bundlesfilter command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        return

    global BundlesFilterEnabled
    text = message.text.lower().replace('/bundlesfilter', '').strip()
    if text == "yes":
        BundlesFilterEnabled = True
        await message.answer("Bundles filter set to: Yes ✅")
        logger.info("Bundles filter enabled")
    elif text == "no":
        BundlesFilterEnabled = False
        await message.answer("Bundles filter set to: No 🚫")
        logger.info("Bundles filter disabled")
    else:
        await message.answer("Please specify Yes or No after /bundlesfilter (e.g., /bundlesfilter Yes) 🤔")

# Insiders
@dp.message(Command(commands=["setinsiders"]))
async def set_insiders(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setinsiders command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        return

    global InsidersThreshold
    text = message.text.lower().replace('/setinsiders', '').strip()
    try:
        value = float(text)
        InsidersThreshold = value
        await message.answer(f"InsidersThreshold set to: {InsidersThreshold} ✅")
        logger.info(f"InsidersThreshold updated to: {InsidersThreshold}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /setinsiders 10) 🚫")

@dp.message(Command(commands=["insidersfilter"]))
async def toggle_insiders_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /insidersfilter command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        return

    global InsidersFilterEnabled
    text = message.text.lower().replace('/insidersfilter', '').strip()
    if text == "yes":
        InsidersFilterEnabled = True
        await message.answer("Insiders filter set to: Yes ✅")
        logger.info("Insiders filter enabled")
    elif text == "no":
        InsidersFilterEnabled = False
        await message.answer("Insiders filter set to: No 🚫")
        logger.info("Insiders filter disabled")
    else:
        await message.answer("Please specify Yes or No after /insidersfilter (e.g., /insidersfilter Yes) 🤔")

# KOLs
@dp.message(Command(commands=["setkols"]))
async def set_kols(message: types.Message):
    username = message.from_user.username
    logger

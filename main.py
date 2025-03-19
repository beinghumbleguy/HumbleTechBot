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
dp = Dispatcher()  # Define dp here
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

# Define VIP channels (updated to include the correct negative ID)
VIP_CHANNEL_IDS = {-1002272066154, -1002280798125}  # Added both channel IDs {-1002272066154, -1002280798125}

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
        DevSoldThreshold = text.capitalize()  # Convert "yes" to "Yes", "no" to "No"
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
    logger.info(f"Received /setkols command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        return

    global KOLsThreshold
    text = message.text.lower().replace('/setkols', '').strip()
    try:
        value = float(text)
        KOLsThreshold = value
        await message.answer(f"KOLsThreshold set to: {KOLsThreshold} ✅")
        logger.info(f"KOLsThreshold updated to: {KOLsThreshold}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /setkols 1) 🚫")

@dp.message(Command(commands=["kolsfilter"]))
async def toggle_kols_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /kolsfilter command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        return

    global KOLsFilterEnabled
    text = message.text.lower().replace('/kolsfilter', '').strip()
    if text == "yes":
        KOLsFilterEnabled = True
        await message.answer("KOLs filter set to: Yes ✅")
        logger.info("KOLs filter enabled")
    elif text == "no":
        KOLsFilterEnabled = False
        await message.answer("KOLs filter set to: No 🚫")
        logger.info("KOLs filter disabled")
    else:
        await message.answer("Please specify Yes or No after /kolsfilter (e.g., /kolsfilter Yes) 🤔")

# Handler for /downloadcsv command
@dp.message(Command(commands=["downloadcsv"]))
async def download_csv_command(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /downloadcsv command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /downloadcsv attempt by @{username}")
        return

    base_url = os.getenv("RAILWAY_PUBLIC_DOMAIN", "http://localhost:5000")
    if base_url == "http://localhost:5000" and "RAILWAY_PUBLIC_DOMAIN" not in os.environ:
        logger.warning("RAILWAY_PUBLIC_DOMAIN not set, using localhost:5000 (this won't work on Railway)")
    download_url = f"{base_url}/download/csv?token={DOWNLOAD_TOKEN}"

    if not os.path.exists(CSV_FILE):
        await message.answer("⚠️ No CSV file exists yet. Process some messages to generate data.")
        logger.info("CSV file not found for /downloadcsv")
        return

    await message.answer(
        f"Click the link to download or view the CSV file:\n{download_url}\n"
        "Note: This link is private and should not be shared."
    )
    logger.info(f"Provided CSV download link to @{username}: {download_url}")

# Handler for /ca <token_ca> command
@dp.message(Command(commands=["ca"]))
async def cmd_ca(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /ca command from {username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /ca attempt by {username}")
        return

    text = message.text
    parts = text.split()
    if len(parts) != 2:
        await message.answer("Usage: /ca <token_ca>")
        return

    token_ca = parts[1].strip()
    logger.info(f"Processing token CA: {token_ca}")

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

# Handler for /mastersetup command to display all filter settings
@dp.message(Command(commands=["mastersetup"]))
async def master_setup(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /mastersetup command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /mastersetup attempt by @{username}")
        return

    # Build the response with all filter settings
    response = "📋 **Master Setup - Current Filter Configurations**\n\n"
    
    # Filter toggles
    response += "🔧 **Filter Toggles**\n"
    response += f"- Filter Enabled: {filter_enabled}\n"
    response += f"- CheckHigh Enabled: {CheckHighEnabled}\n"
    response += f"- CheckLow Enabled: {CheckLowEnabled}\n"
    response += f"- DevSold Filter Enabled: {DevSoldFilterEnabled}\n"
    response += f"- Top10 Filter Enabled: {Top10FilterEnabled}\n"
    response += f"- Snipers Filter Enabled: {SniphersFilterEnabled}\n"
    response += f"- Bundles Filter Enabled: {BundlesFilterEnabled}\n"
    response += f"- Insiders Filter Enabled: {InsidersFilterEnabled}\n"
    response += f"- KOLs Filter Enabled: {KOLsFilterEnabled}\n\n"

    # Thresholds
    response += "📊 **Threshold Settings**\n"
    # Escape special characters in variable values
    pass_value_str = str(PassValue) if PassValue is not None else "Not set"
    range_low_str = str(RangeLow) if RangeLow is not None else "Not set"
    dev_sold_threshold_str = str(DevSoldThreshold) if DevSoldThreshold is not None else "Not set"
    dev_sold_left_str = str(DevSoldLeft) if DevSoldLeft is not None else "Not set"
    top_10_threshold_str = str(Top10Threshold) if Top10Threshold is not None else "Not set"
    snipers_threshold_str = str(SnipersThreshold) if SnipersThreshold is not None else "Not set"
    bundles_threshold_str = str(BundlesThreshold) if BundlesThreshold is not None else "Not set"
    insiders_threshold_str = str(InsidersThreshold) if InsidersThreshold is not None else "Not set"
    kols_threshold_str = str(KOLsThreshold) if KOLsThreshold is not None else "Not set"

    # Function to escape Markdown special characters
    def escape_markdown(text):
        special_chars = r'\*_`\[\]\(\)#\+-=!|{}\.%'
        return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', text)

    # Log byte offsets for debugging
    lines = [
        f"- PassValue (CheckHigh): {escape_markdown(pass_value_str)}\n",
        f"- RangeLow (CheckLow): {escape_markdown(range_low_str)}\n",
        f"- DevSold Threshold: {escape_markdown(dev_sold_threshold_str)}\n",
        f"- DevSoldLeft Threshold: {escape_markdown(dev_sold_left_str)}%\n",
        f"- Top10 Threshold: {escape_markdown(top_10_threshold_str)}\n",
        f"- Snipers Threshold: {escape_markdown(snipers_threshold_str)}\n",
        f"- Bundles Threshold: {escape_markdown(bundles_threshold_str)}\n",
        f"- Insiders Threshold: {escape_markdown(insiders_threshold_str)}\n",
        f"- KOLs Threshold: {escape_markdown(kols_threshold_str)}\n"
    ]
    
    # Calculate byte offsets for each line to pinpoint the error
    current_offset = len(response.encode('utf-8'))
    for i, line in enumerate(lines):
        logger.info(f"Line {i+1} byte offset: {current_offset} - {line.strip()}")
        response += line
        current_offset += len(line.encode('utf-8'))

    response += "\n🔍 Use the respective /set* and /filter commands to adjust these settings."

    # Log the full response for debugging
    logger.info(f"Full master setup response: {response}")

    try:
        logger.info(f"Sending master setup response: {response[:100]}...")  # Log first 100 chars to avoid flooding
        await message.answer(response, parse_mode="Markdown")
        logger.info("Master setup response sent successfully")
    except Exception as e:
        logger.error(f"Failed to send master setup response: {e}")
        # Fallback: Try sending without Markdown parsing
        logger.info("Retrying without Markdown parsing...")
        await message.answer(response, parse_mode=None)
        logger.info("Sent response without Markdown parsing as a fallback")

# Handler for messages (acting as /button and /filter logic, excluding commands)
@dp.message(F.text, ~F.text.startswith('/'))
@dp.channel_post(F.text, ~F.text.startswith('/'))
async def convert_link_to_button(message: types.Message):
    logger.info(f"Received full message text: {message.text}")
    logger.info(f"Chat type: {message.chat.type}")
    logger.info(f"Original message ID: {message.message_id}")
    logger.info(f"Forwarded from: {message.forward_from_chat}")
    logger.info(f"Entities: {message.entities}")
    logger.info(f"Filter enabled state: {filter_enabled}")
    logger.info(f"Current PassValue: {PassValue}")
    logger.info(f"Current RangeLow: {RangeLow}")
    logger.info(f"Chat ID: {message.chat.id}")  # Log the channel ID

    if message.forward_from_chat:
        logger.info(f"Message is forwarded from chat: {message.forward_from_chat.title}")

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

    # If no URL entity, try to find CA in plain text
    if not ca:
        ca_match = re.search(r'[A-Za-z0-9]{44}', text)
        if ca_match:
            ca = ca_match.group(0)
            logger.info(f"Extracted CA from plain text: {ca}")

    # Extract BuyPercent, SellPercent, and other filter values
    has_buy_sell = False
    buy_percent = None
    sell_percent = None
    dev_sold = None  # "Yes" or "No"
    dev_sold_left_value = None  # Percentage left if dev_sold is "No"
    top_10 = None
    snipers = None
    bundles = None  # Default to 0 if not found
    insiders = None
    kols = None
    lines = [line.strip() for line in text.replace('\r\n', '\n').split('\n') if line.strip()]
    logger.info(f"Lines to check: {lines}")

    for line in lines:
        logger.info(f"Checking line: '{line}'")
        match_bs = re.search(r'├?Sum\s*🅑:\s*(\d+\.?\d*)%\s*[\|]\s*Sum\s*🅢:\s*(\d+\.?\d*)%', line)
        if match_bs:
            has_buy_sell = True
            buy_percent = float(match_bs.group(1))
            sell_percent = float(match_bs.group(2))
            logger.info(f"Found BuyPercent and SellPercent: {match_bs.group(0)} with groups: {match_bs.groups()}")
            continue

        # Dev sold (Yes/No based on emoji)
        match_dev_yes = re.search(r'├?Dev:\s*✅\s*\(sold\)', line)
        match_dev_no = re.search(r'├?Dev:\s*❌\s*\((\d+\.?\d*)%\s*left\)', line)
        if match_dev_yes:
            dev_sold = "Yes"
            dev_sold_left_value = None
            logger.info(f"Found DevSold: {dev_sold}")
            continue
        elif match_dev_no:
            dev_sold = "No"
            dev_sold_left_value = float(match_dev_no.group(1))
            logger.info(f"Found DevSold: {dev_sold}, Left: {dev_sold_left_value}%")
            continue

        match_top10 = re.search(r'├?Top 10:\s*(\d+\.?\d*)', line)
        if match_top10:
            top_10 = float(match_top10.group(1))
            logger.info(f"Found Top10: {top_10}")
            continue

        match_snipers = re.search(r'├?Sniper:\s*(\d+\.?\d*)', line)
        if match_snipers:
            snipers = float(match_snipers.group(1))
            logger.info(f"Found Snipers: {snipers}")
            continue

        match_bundles = re.search(r'├?Bundle:.*buy\s*(\d+\.?\d*)%', line)
        if match_bundles:
            bundles = float(match_bundles.group(1))
            logger.info(f"Found Bundles: {bundles}")
            continue

        match_insiders = re.search(r'├?🐁Insiders:\s*(\d+\.?\d*)', line)
        if match_insiders:
            insiders = float(match_insiders.group(1))
            logger.info(f"Found Insiders: {insiders}")
            continue

        match_kols = re.search(r'└?🌟KOLs:\s*(\d+\.?\d*)', line)
        if match_kols:
            kols = float(match_kols.group(1))
            logger.info(f"Found KOLs: {kols}")
            continue

    # Default bundles to 0 if not found
    if bundles is None:
        bundles = 0
        logger.info("No Bundles percentage found, defaulting to 0")

    # Process filters if BuyPercent/SellPercent exists
    if has_buy_sell:
        logger.info("Message contains BuyPercent/SellPercent, processing filters")
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
                logger.warning("SellPercent is 0, assuming infinity")
                bs_ratio = float('inf')
            else:
                bs_ratio = buy_percent / sell_percent
                logger.info(f"Calculated BSRatio: {buy_percent} / {sell_percent} = {bs_ratio}")
        except Exception as e:
            logger.error(f"Error calculating BSRatio: {e}")
            bs_ratio = 0

        # Check if required thresholds are set for enabled filters
        missing_vars = []
        if (CheckHighEnabled or CheckLowEnabled) and PassValue is None:
            missing_vars.append("PassValue (use /setupval)")
        if CheckLowEnabled and RangeLow is None:
            missing_vars.append("RangeLow (use /setrangelow)")
        if DevSoldFilterEnabled and DevSoldThreshold is None:
            missing_vars.append("DevSoldThreshold (use /setdevsold Yes|No)")
        if DevSoldFilterEnabled and DevSoldThreshold == "Yes" and dev_sold == "No" and DevSoldLeft is None:
            missing_vars.append("DevSoldLeft (use /setdevsoldleft)")
        if Top10FilterEnabled and Top10Threshold is None:
            missing_vars.append("Top10Threshold (use /settop10)")
        if SniphersFilterEnabled and SnipersThreshold is None:
            missing_vars.append("SnipersThreshold (use /setsnipers)")
        if BundlesFilterEnabled and BundlesThreshold is None:
            missing_vars.append("BundlesThreshold (use /setbundles)")
        if InsidersFilterEnabled and InsidersThreshold is None:
            missing_vars.append("InsidersThreshold (use /setinsiders)")
        if KOLsFilterEnabled and KOLsThreshold is None:
            missing_vars.append("KOLsThreshold (use /setkols)")

        if missing_vars:
            await message.answer(f"⚠️ Please set {', '.join(missing_vars)} before filtering.")
            return

        # Evaluate each filter
        filter_results = []
        all_filters_pass = True
        check_high_pass = None
        check_low_pass = None
        dev_sold_pass = None
        top_10_pass = None
        snipers_pass = None
        bundles_pass = None
        insiders_pass = None
        kols_pass = None

        # BSRatio (OR condition: >= PassValue OR 1 <= BSRatio <= RangeLow)
        if CheckHighEnabled or CheckLowEnabled:
            bs_ratio_pass = (bs_ratio >= PassValue) or (1 <= bs_ratio <= RangeLow) if RangeLow is not None else (bs_ratio >= PassValue)
            filter_results.append(f"BSRatio: {bs_ratio:.2f} {'✅' if bs_ratio_pass else '🚫'} (Threshold: >= {PassValue} or 1 to {RangeLow if RangeLow else 'N/A'})")
            if not bs_ratio_pass:
                all_filters_pass = False
            logger.info(f"BSRatio check: {bs_ratio_pass} - Condition: >= {PassValue} or 1 <= {bs_ratio} <= {RangeLow if RangeLow else 'N/A'}")
        else:
            filter_results.append(f"BSRatio: {bs_ratio:.2f} (Disabled)")

        # DevSold (Yes/No comparison with percentage left check)
        if DevSoldFilterEnabled:
            if dev_sold is None:
                filter_results.append("DevSold: Not found in message 🚫")
                all_filters_pass = False
                logger.info("DevSold: Not found in message")
            elif DevSoldThreshold is None:
                filter_results.append("DevSold: Threshold not set 🚫 (use /setdevsold Yes|No)")
                all_filters_pass = False
                logger.info("DevSold: Threshold not set")
            else:
                logger.info(f"Evaluating DevSold: dev_sold={dev_sold}, DevSoldThreshold={DevSoldThreshold}, dev_sold_left_value={dev_sold_left_value}, DevSoldLeft={DevSoldLeft}")
                if dev_sold == "Yes":
                    dev_sold_pass = True
                    filter_results.append(f"DevSold: {dev_sold} {'✅' if dev_sold_pass else '🚫'} (Passes because DevSold is Yes)")
                elif dev_sold == "No":
                    if DevSoldThreshold == "Yes":
                        if DevSoldLeft is None:
                            filter_results.append("DevSold: DevSoldLeft threshold not set 🚫 (use /setdevsoldleft)")
                            dev_sold_pass = False
                        elif dev_sold_left_value is not None:
                            dev_sold_pass = dev_sold_left_value <= DevSoldLeft
                            filter_results.append(
                                f"DevSold: {dev_sold} ({dev_sold_left_value}% left) {'✅' if dev_sold_pass else '🚫'} (Threshold: {DevSoldThreshold}, Left <= {DevSoldLeft}%)"
                            )
                        else:
                            dev_sold_pass = False
                            filter_results.append(f"DevSold: {dev_sold} (No percentage left data) {'✅' if dev_sold_pass else '🚫'} (Threshold: {DevSoldThreshold})")
                    else:
                        # If DevSoldThreshold is "No" and dev_sold is "No", fail because we're looking for "Yes"
                        dev_sold_pass = False
                        filter_results.append(f"DevSold: {dev_sold} {'✅' if dev_sold_pass else '🚫'} (Threshold: {DevSoldThreshold})")
                else:
                    # Unexpected value for dev_sold
                    dev_sold_pass = False
                    filter_results.append(f"DevSold: {dev_sold} {'✅' if dev_sold_pass else '🚫'} (Invalid value)")
                if not dev_sold_pass:
                    all_filters_pass = False
                logger.info(f"DevSold: {dev_sold_pass}")
        else:
            filter_results.append(f"DevSold: {dev_sold if dev_sold else 'Not found'} (Disabled)")

        # Top10 (Pass if <= Top10Threshold)
        if Top10FilterEnabled and top_10 is not None:
            top_10_pass = top_10 <= Top10Threshold
            filter_results.append(f"Top10: {top_10} {'✅' if top_10_pass else '🚫'} (Threshold: <= {Top10Threshold})")
            if not top_10_pass:
                all_filters_pass = False
            logger.info(f"Top10: {top_10_pass} - Condition: <= {Top10Threshold}")
        elif Top10FilterEnabled and top_10 is None:
            filter_results.append("Top10: Not found in message 🚫")
        else:
            filter_results.append(f"Top10: {top_10 if top_10 else 'Not found'} (Disabled)")

        # Snipers (Pass if <= SnipersThreshold)
        if SniphersFilterEnabled and snipers is not None:
            snipers_pass = snipers <= SnipersThreshold
            filter_results.append(f"Snipers: {snipers} {'✅' if snipers_pass else '🚫'} (Threshold: <= {SnipersThreshold})")
            if not snipers_pass:
                all_filters_pass = False
            logger.info(f"Snipers: {snipers_pass} - Condition: <= {SnipersThreshold}")
        elif SniphersFilterEnabled and snipers is None:
            filter_results.append("Snipers: Not found in message 🚫")
        else:
            filter_results.append(f"Snipers: {snipers if snipers else 'Not found'} (Disabled)")

        # Bundles (Pass if <= BundlesThreshold)
        if BundlesFilterEnabled and bundles is not None:
            bundles_pass = bundles <= BundlesThreshold
            filter_results.append(f"Bundles: {bundles} {'✅' if bundles_pass else '🚫'} (Threshold: <= {BundlesThreshold})")
            if not bundles_pass:
                all_filters_pass = False
            logger.info(f"Bundles: {bundles_pass} - Condition: <= {BundlesThreshold}")
        elif BundlesFilterEnabled and bundles is None:
            filter_results.append("Bundles: Not found in message 🚫")
        else:
            filter_results.append(f"Bundles: {bundles if bundles else 'Not found'} (Disabled)")

        # Insiders (Fail if >= InsidersThreshold)
        if InsidersFilterEnabled and insiders is not None:
            insiders_pass = insiders < InsidersThreshold  # Pass if less than threshold, fail if >=
            filter_results.append(f"Insiders: {insiders} {'✅' if insiders_pass else '🚫'} (Threshold: < {InsidersThreshold})")
            if not insiders_pass:
                all_filters_pass = False
            logger.info(f"Insiders: {insiders_pass} - Condition: < {InsidersThreshold}")
        elif InsidersFilterEnabled and insiders is None:
            filter_results.append("Insiders: Not found in message 🚫")
        else:
            filter_results.append(f"Insiders: {insiders if insiders else 'Not found'} (Disabled)")

        # KOLs (Pass if >= KOLsThreshold)
        if KOLsFilterEnabled and kols is not None:
            kols_pass = kols >= KOLsThreshold  # Pass if greater than or equal to threshold, fail otherwise
            filter_results.append(f"KOLs: {kols} {'✅' if kols_pass else '🚫'} (Threshold: >= {KOLsThreshold})")
            if not kols_pass:
                all_filters_pass = False
            logger.info(f"KOLs: {kols_pass} - Condition: >= {KOLsThreshold}")
        elif KOLsFilterEnabled and kols is None:
            filter_results.append("KOLs: Not found in message 🚫")
        else:
            filter_results.append(f"KOLs: {kols if kols else 'Not found'} (Disabled)")

        # Log to CSV
        log_to_csv(
            ca, bs_ratio, bs_ratio_pass if (CheckHighEnabled or CheckLowEnabled) else None, None,
            dev_sold, dev_sold_left_value, dev_sold_pass,
            top_10, top_10_pass, snipers, snipers_pass,
            bundles, bundles_pass, insiders, insiders_pass,
            kols, kols_pass, all_filters_pass
        )

        # Check if any filters are enabled
        any_filter_enabled = (CheckHighEnabled or CheckLowEnabled or DevSoldFilterEnabled or
                             Top10FilterEnabled or SniphersFilterEnabled or BundlesFilterEnabled or
                             InsidersFilterEnabled or KOLsFilterEnabled)

        # Prepare output
        if not any_filter_enabled:
            output_text = f"No filters are enabled. Please enable at least one filter to evaluate CA.\n**{first_line}**\n**{second_line}**"
        elif all_filters_pass:
            filter_summary = "\n".join(filter_results)
            output_text = f"Filter Passed: 🎉\n**{first_line}**\n**{second_line}**\n{filter_summary}"
        else:
            filter_summary = "\n".join(filter_results)
            output_text = f"CA did not qualify: 🚫\n**{first_line}**\n**{second_line}**\n{filter_summary}"

        entities = []
        if ca:
            ca_match = re.search(r'[A-Za-z0-9]{44}', output_text)
            if ca_match:
                ca = ca_match.group(0)
                text_before_ca = output_text[:output_text.find(ca)]
                ca_new_offset = len(text_before_ca.encode('utf-16-le')) // 2
                ca_length = 44
                # Add CA as a copyable entity (using pre-formatted text for easy copying)
                entities.append(types.MessageEntity(
                    type="pre",  # Use "pre" to make it selectable and copyable
                    offset=ca_new_offset,
                    length=ca_length
                ))
                logger.info(f"Added CA as copyable entity: {ca} at offset {ca_new_offset}")

        try:
            logger.info("Creating new message for output")
            new_message = await message.answer(output_text, entities=entities, parse_mode="Markdown")
            logger.info(f"New message ID: {new_message.message_id}")
        except Exception as e:
            logger.error(f"Error creating new message: {e}")
        return

    # Default /button functionality
    if ca and "reflink" in message.text.lower():
        logger.info(f"Adding buttons because 'reflink' found in message: {message.text}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            # Add "Join VIP" button if the channel is in VIP_CHANNEL_IDS
            [InlineKeyboardButton(text="🌟🚀 Join VIP 🚀🌟", url="https://t.me/HumbleMoonshotsPay_bot?start=start")] 
            if message.chat.id in VIP_CHANNEL_IDS else [],
            [
                InlineKeyboardButton(text="Bloom", url=f"https://t.me/BloomSolana_bot?start=ref_humbleguy_ca_{ca}"),
                InlineKeyboardButton(text="Fasol", url=f"https://t.me/fasol_robot?start=ref_humbleguy_ca_{ca}"),
            ],
            [
                InlineKeyboardButton(text="Maestro", url=f"http://t.me/maestro?start={ca}-beinghumbleguy"),
                InlineKeyboardButton(text="Trojan", url=f"https://t.me/solana_trojanbot?start=r-beinghumbleguy-{ca}")
            ]
        ])
        text = re.sub(r'Forwarded from .*\n', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Buy token on Fasol Reflink', '', text, flags=re.IGNORECASE)
        # Keep CA but ensure it's not replaced or made copyable
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if re.search(r'[A-Za-z0-9]{44}', line):
                lines[i] = f"🔗 CA: {ca}"  # Keep CA but format it as plain text for editing
                break
        text = "\n".join(line.strip() for line in lines if line.strip())
        logger.info(f"Final text to send (CA included): {text}")

        entities = []
        if ca:
            ca_match = re.search(r'[A-Za-z0-9]{44}', text)
            if ca_match:
                ca = ca_match.group(0)
                text_before_ca = text[:text.find(ca)]
                ca_new_offset = len(text_before_ca.encode('utf-16-le')) // 2
                ca_length = 44
                # Add CA as a copyable entity
                entities.append(types.MessageEntity(
                    type="pre",  # Use "pre" to make it selectable and copyable
                    offset=ca_new_offset,
                    length=ca_length
                ))
                logger.info(f"Added CA as copyable entity: {ca} at offset {ca_new_offset}")

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

async def main():
    # Initialize CSV file
    init_csv()

    commands = [
        BotCommand(command="filter", description="Enable or disable the filter (Yes/No)"),
        BotCommand(command="setupval", description="Set PassValue for CheckHigh (e.g., /setupval 1.2)"),
        BotCommand(command="setrangelow", description="Set RangeLow for CheckLow (e.g., /setrangelow 1.1)"),
        BotCommand(command="checkhigh", description="Enable/disable CheckHigh filter (Yes/No)"),
        BotCommand(command="checklow", description="Enable/disable CheckLow filter (Yes/No)"),
        BotCommand(command="setdevsold", description="Set DevSold threshold (Yes/No) (e.g., /setdevsold Yes)"),
        BotCommand(command="setdevsoldleft", description="Set DevSoldLeft threshold (e.g., /setdevsoldleft 10)"),
        BotCommand(command="devsoldfilter", description="Enable/disable DevSold filter (Yes/No)"),
        BotCommand(command="settop10", description="Set Top10 threshold (e.g., /settop10 20)"),
        BotCommand(command="top10filter", description="Enable/disable Top10 filter (Yes/No)"),
        BotCommand(command="setsnipers", description="Set Snipers threshold (e.g., /setsnipers 3)"),
        BotCommand(command="snipersfilter", description="Enable/disable Snipers filter (Yes/No)"),
        BotCommand(command="setbundles", description="Set Bundles threshold (e.g., /setbundles 1)"),
        BotCommand(command="bundlesfilter", description="Enable/disable Bundles filter (Yes/No)"),
        BotCommand(command="setinsiders", description="Set Insiders threshold (e.g., /setinsiders 10)"),
        BotCommand(command="insidersfilter", description="Enable/disable Insiders filter (Yes/No)"),
        BotCommand(command="setkols", description="Set KOLs threshold (e.g., /setkols 1)"),
        BotCommand(command="kolsfilter", description="Enable/disable KOLs filter (Yes/No)"),
        BotCommand(command="adduser", description="Add an authorized user (only for @BeingHumbleGuy)"),
        BotCommand(command="ca", description="Get token data (e.g., /ca <token_ca>)"),
        BotCommand(command="downloadcsv", description="Get link to download the CSV log (authorized users only)"),
        BotCommand(command="mastersetup", description="Display all current filter settings")
    ]
    
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

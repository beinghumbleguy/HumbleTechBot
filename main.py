# Chunk 1 starts
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, BotCommand, Message
from aiogram.filters import Command, BaseFilter
import asyncio
import logging
import os
import csv
import re
from flask import Flask, send_file, request, abort, jsonify
from threading import Thread
import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import threading
import secrets
import time
import random
import aiohttp
import tls_client
import tweepy
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict
from cachetools import TTLCache
import pytz
import aiogram
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Enable debug logging

import base64

"""
# New comment
import os
import hashlib
import secrets


code_verifier = secrets.token_urlsafe(32)
print(f"code_verifier: {code_verifier}")
code_challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
code_challenge = base64.urlsafe_b64encode(code_challenge_bytes).rstrip(b'=').decode('utf-8')
print(f"code_challenge: {code_challenge}")
os.environ['X_CODE_VERIFIER'] = code_verifier  # Store temporarily
"""


"""
import requests
import os
import base64

# Retrieve credentials (use environment variables or replace placeholders)
client_id = os.getenv("X_CLIENT_ID", "ck00cUFPMFY5c3NGbkcyU3BpcEU6MTpjaQ")  # Your Client ID
client_secret = os.getenv("X_CLIENT_SECRET", "<your_client_secret_here>")  # Replace with your Client Secret
code = "VVprRHNaV2prVWszd3BXNzg1a1c0QTVTZm41Y2oyQTJZcHpXTmlhMFhLUXNIOjE3NTMzMzcyODM2OTE6MTowOmFjOjE"  # The code from the redirect
code_verifier = os.getenv("X_CODE_VERIFIER", "<your_code_verifier_here>")  # Replace with your code_verifier
redirect_uri = "https://humbletechbot-production.up.railway.app/api/auth/callback/twitter"  # Match the used URI

# Create Basic Authentication header
auth_string = f"{client_id}:{client_secret}"
auth_header = base64.b64encode(auth_string.encode()).decode()
headers = {
    "Authorization": f"Basic {auth_header}",
    "Content-Type": "application/x-www-form-urlencoded"
}

# Prepare the request
url = "https://api.twitter.com/2/oauth2/token"
data = {
    "code": code,
    "grant_type": "authorization_code",
    "redirect_uri": redirect_uri,
    "code_verifier": code_verifier
}

# Make the POST request
response = requests.post(url, data=data, headers=headers)

# Check and print the response
if response.status_code == 200:
    token_data = response.json()
    access_token = token_data["access_token"]
    print(f"Access Token: {access_token}")
    if "refresh_token" in token_data:
        print(f"Refresh Token: {token_data['refresh_token']}")
    # Update this token in Railway manually
    os.environ["X_ACCESS_TOKEN"] = access_token  # Temporary local set
    print("Update Railway with this X_ACCESS_TOKEN value.")
else:
    print(f"Error: {response.status_code} - {response.text}")

# Note: For production, save the token securely in Railway, not just locally
"""
# Chunk 1 (partial update)

import logging
import aiogram

# Custom filter to suppress "Raw update received" logs
class SuppressRawUpdateFilter(logging.Filter):
    def filter(self, record):
        return "Raw update received" not in record.getMessage()

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)  # __name__ is "__main__" in the main script

# Apply the filter to the __main__ logger to suppress "Raw update received"
logger.addFilter(SuppressRawUpdateFilter())

logger.info(f"Using Aiogram version: {aiogram.__version__}")

# Chunk 1 starts
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, BotCommand
from aiogram.filters import Command, BaseFilter
import asyncio
import logging
import os
import csv
import re
from flask import Flask, send_file, request, abort
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor
import secrets
from cachetools import TTLCache
from datetime import datetime
import pytz
import time

# Custom filter to detect non-command messages
class NotCommandFilter(BaseFilter):
    def __call__(self, message: types.Message) -> bool:
        logger.debug(f"NotCommandFilter checking message: '{message.text}'")
        result = bool(message.text and not message.text.startswith('/'))
        logger.debug(f"NotCommandFilter result: {result}")
        return result

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
router = Router()

# Thread locks for safe CSV writing
csv_lock = Lock()
growth_csv_lock = Lock()
monitored_tokens_lock = Lock()

# Thread pool executor for running blocking tasks
_executor = ThreadPoolExecutor(max_workers=5)

# Global variables with default values
filter_enabled = True
PassValue = 1.3
RangeLow = 1.08
authorized_users = ["@BeingHumbleGuy"]
additional_user_added = False

# BSRatio filter toggles
CheckHighEnabled = True
CheckLowEnabled = True

# New filter thresholds
DevSoldThreshold = "Yes"
DevSoldLeft = 6.0
Top10Threshold = 52.0
SnipersThreshold = 10.0
BundlesThreshold = 3.0
InsidersThreshold = 3.0
KOLsThreshold = 0.0
BondingCurveThreshold = 80.0

# New filter toggles
DevSoldFilterEnabled = True
Top10FilterEnabled = True
SniphersFilterEnabled = True
BundlesFilterEnabled = True
InsidersFilterEnabled = True
KOLsFilterEnabled = True
BondingCurveFilterEnabled = True

# Growth check variables
growth_notifications_enabled = True
GROWTH_THRESHOLD = 1.5
INCREMENT_THRESHOLD = 1.0
CHECK_INTERVAL = 30  # Changed to 30 seconds from 300
# DAILY_REPORT_INTERVAL = 14400  # Interval for daily_summary_report (4 hours) in seconds
DAILY_REPORT_INTERVAL = 7200  # Interval for daily_summary_report (4 hours) in seconds
PNL_REPORT_INTERVAL = 21600 # 6 hours
MONITORING_DURATION = 21600  # 6 hours in seconds
monitored_tokens = {}
last_growth_ratios = {}

# Define channel IDs
VIP_CHANNEL_IDS = {-1002365061913}
PUBLIC_CHANNEL_IDS = {-1002272066154}
VIP_CHAT_IDS = {-1002497412722}

# CSV file paths
PUBLIC_CSV_FILE = "/app/data/public_ca_filter_log.csv"
VIP_CSV_FILE = "/app/data/vip_ca_filter_log.csv"
PUBLIC_GROWTH_CSV_FILE = "/app/data/public_growthcheck_log.csv"
VIP_GROWTH_CSV_FILE = "/app/data/vip_growthcheck_log.csv"
MONITORED_TOKENS_CSV_FILE = "/app/data/monitored_tokens.csv"

# Secret token for securing the Flask download route
DOWNLOAD_TOKEN = secrets.token_urlsafe(32)
logger.info(f"Generated download token: {DOWNLOAD_TOKEN}")

# Initialize cache for API responses (TTL of 1 hour)
token_data_cache = TTLCache(maxsize=1000, ttl=3600)


# Include router in dispatcher
dp.include_router(router)

# Test tweet command handler with OAuth 2.0
logger.debug("Using updated test_tweet function from cgpt")
import os
import tweepy
#from aiogram import F
#from aiogram.types import Message
#from your_router_module import router  # adjust as needed

@router.message(F.text.startswith('/testtweet'))
async def test_tweet(message: Message):
    try:
        bearer_token = os.getenv("X_BEARER_TOKEN")
        consumer_key = os.getenv("X_CONSUMER_KEY")
        consumer_secret = os.getenv("X_CONSUMER_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

        if not all([bearer_token, consumer_key, consumer_secret, access_token, access_token_secret]):
            await message.reply("❌ Error: Missing one or more Twitter OAuth 2.0 credentials.")
            return

        # Use Twitter API v2 Client
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )

        tweet_text = "🚀 This is a test tweet from Humble Gems via v2 API"
        response = client.create_tweet(text=tweet_text)

        if response and response.data and response.data.get("id"):
            await message.reply("✅ Test tweet posted successfully via v2 API!")
        else:
            await message.reply(f"⚠️ Something went wrong: {response}")
    except Exception as e:
        await message.reply(f"❌ Failed to post tweet:\n{e}")
        
# Initialize CSV files with headers
def init_csv():
    data_dir = "/app/data"
    try:
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Ensured directory exists: {data_dir}")
    except Exception as e:
        logger.error(f"Failed to create directory {data_dir}: {str(e)}")
        raise

    for csv_file in [PUBLIC_CSV_FILE, VIP_CSV_FILE]:
        if not os.path.exists(csv_file):
            with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "CA", "TokenName", "BSRatio", "BSRatio_Pass", "BSRatio_Low_Pass",
                    "DevSold", "DevSoldLeftValue", "DevSold_Pass", "Top10", "Top10_Pass",
                    "Snipers", "Snipers_Pass", "Bundles", "Bundles_Pass", "Insiders", "Insiders_Pass",
                    "KOLs", "Kols_Pass", "BondingCurve", "BCPass", "Overall_Pass", 
                    "OriginalMC", "CurrentMC", "GrowthRatio"
                ])
            logger.info(f"Initialized filter CSV file: {csv_file}")

    for csv_file in [PUBLIC_GROWTH_CSV_FILE, VIP_GROWTH_CSV_FILE]:
        if not os.path.exists(csv_file):
            with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "ChatID", "ChannelID", "MessageID", "TokenName", "CA",
                    "OriginalMC", "CurrentMC", "GrowthRatio", "ProfitPercent", "TimeSinceAdded"
                ])
            logger.info(f"Initialized growth check CSV file: {csv_file}")

    # Enhanced initialization for monitored_tokens.csv
    if not os.path.exists(MONITORED_TOKENS_CSV_FILE):
        try:
            with open(MONITORED_TOKENS_CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["CA:ChatID", "TokenName", "InitialMC", "PeakMC", "Timestamp", "MessageID", "ChatID"])
            logger.info(f"Initialized monitored tokens CSV file: {MONITORED_TOKENS_CSV_FILE}")
        except Exception as e:
            logger.error(f"Failed to initialize {MONITORED_TOKENS_CSV_FILE}: {str(e)}")
            raise
    else:
        # Ensure file is readable and has headers
        try:
            with open(MONITORED_TOKENS_CSV_FILE, mode='r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if not headers or headers != ["CA:ChatID", "TokenName", "InitialMC", "PeakMC", "Timestamp", "MessageID", "ChatID"]:
                    logger.warning(f"Invalid headers in {MONITORED_TOKENS_CSV_FILE}, reinitializing")
                    with open(MONITORED_TOKENS_CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(["CA:ChatID", "TokenName", "InitialMC", "PeakMC", "Timestamp", "MessageID", "ChatID"])
                    logger.info(f"Reinitialized {MONITORED_TOKENS_CSV_FILE} with correct headers")
        except Exception as e:
            logger.error(f"Error checking {MONITORED_TOKENS_CSV_FILE}: {str(e)}")
            raise

# Load monitored tokens from CSV
def load_monitored_tokens():
    global monitored_tokens
    monitored_tokens = {}
    if os.path.exists(MONITORED_TOKENS_CSV_FILE):
        with open(MONITORED_TOKENS_CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row["CA:ChatID"]  # Updated to composite key
                monitored_tokens[key] = {
                    "token_name": row["TokenName"],
                    "initial_mc": float(row["InitialMC"]),
                    "peak_mc": float(row.get("PeakMC", row["InitialMC"])),  # Default to InitialMC if missing
                    "timestamp": float(row["Timestamp"]),
                    "message_id": int(row["MessageID"]),
                    "chat_id": int(row["ChatID"])
                }
        logger.info(f"Loaded {len(monitored_tokens)} tokens from {MONITORED_TOKENS_CSV_FILE}")
    else:
        logger.info(f"No monitored tokens CSV file found at {MONITORED_TOKENS_CSV_FILE}")

# Save monitored tokens to CSV
def save_monitored_tokens():
    with monitored_tokens_lock:
        with open(MONITORED_TOKENS_CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["CA:ChatID", "TokenName", "InitialMC", "PeakMC", "Timestamp", "MessageID", "ChatID"])
            for key, data in monitored_tokens.items():
                writer.writerow([
                    key,  # Composite key
                    data["token_name"],
                    data["initial_mc"],
                    data.get("peak_mc", data["initial_mc"]),
                    data["timestamp"],
                    data["message_id"],
                    data["chat_id"]
                ])
        logger.info(f"Saved {len(monitored_tokens)} tokens to {MONITORED_TOKENS_CSV_FILE}")

# [Rest of Chunk 1 remains unchanged: log_to_csv, log_to_growthcheck_csv, get_latest_growth_ratio, parse_market_cap, add_user]
# Chunk 1 ends

# Log filter results to CSV
def log_to_csv(ca, token_name, bs_ratio, bs_ratio_pass, check_low_pass, dev_sold, dev_sold_left_value, dev_sold_pass,
               top_10, top_10_pass, snipers, snipers_pass, bundles, bundles_pass,
               insiders, insiders_pass, kols, kols_pass, bonding_curve, bc_pass, overall_pass, 
               original_mc, current_mc, growth_ratio, is_vip_channel):  # Removed market_cap
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    csv_file = VIP_CSV_FILE if is_vip_channel else PUBLIC_CSV_FILE
    # Ensure the directory exists
    os.makedirs(os.path.dirname(csv_file), exist_ok=True)
    with csv_lock:
        rows = []
        updated = False
        if os.path.exists(csv_file):
            with open(csv_file, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                for row in reader:
                    if row["CA"] == ca:
                        # Update existing row
                        rows.append([
                            timestamp, ca, token_name if token_name else row["TokenName"],
                            bs_ratio if bs_ratio is not None else row["BSRatio"],
                            bs_ratio_pass if (CheckHighEnabled or CheckLowEnabled) and bs_ratio_pass is not None else row["BSRatio_Pass"],
                            check_low_pass if CheckLowEnabled and check_low_pass is not None else row["BSRatio_Low_Pass"],
                            dev_sold if dev_sold is not None else row["DevSold"],
                            dev_sold_left_value if dev_sold_left_value is not None else row["DevSoldLeftValue"],
                            dev_sold_pass if DevSoldFilterEnabled and dev_sold_pass is not None else row["DevSold_Pass"],
                            top_10 if top_10 is not None else row["Top10"],
                            top_10_pass if Top10FilterEnabled and top_10_pass is not None else row["Top10_Pass"],
                            snipers if snipers is not None else row["Snipers"],
                            snipers_pass if SniphersFilterEnabled and snipers_pass is not None else row["Snipers_Pass"],
                            bundles if bundles is not None else row["Bundles"],
                            bundles_pass if BundlesFilterEnabled and bundles_pass is not None else row["Bundles_Pass"],
                            insiders if insiders is not None else row["Insiders"],
                            insiders_pass if InsidersFilterEnabled and insiders_pass is not None else row["Insiders_Pass"],
                            kols if kols is not None else row["KOLs"],
                            kols_pass if KOLsFilterEnabled and kols_pass is not None else row["Kols_Pass"],
                            bonding_curve if bonding_curve is not None else row["BondingCurve"],
                            bc_pass if BondingCurveFilterEnabled and bc_pass is not None else row["BCPass"],
                            overall_pass if overall_pass is not None else row["Overall_Pass"],
                            original_mc if original_mc is not None else row.get("OriginalMC", "N/A"),
                            current_mc if current_mc is not None else row.get("CurrentMC", "N/A"),
                            growth_ratio if growth_ratio is not None else row["GrowthRatio"]
                        ])
                        updated = True
                    else:
                        rows.append(list(row.values()))
        if not updated:
            # Append new row if CA not found
            rows.append([
                timestamp, ca if ca else "N/A", token_name if token_name else "N/A",
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
                bonding_curve if bonding_curve is not None else "N/A",
                bc_pass if BondingCurveFilterEnabled and bonding_curve is not None else "N/A",
                overall_pass,
                original_mc if original_mc is not None else "N/A",
                current_mc if current_mc is not None else "N/A",
                growth_ratio if growth_ratio is not None else "N/A"
            ])
        with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "CA", "TokenName", "BSRatio", "BSRatio_Pass", "BSRatio_Low_Pass",
                "DevSold", "DevSoldLeftValue", "DevSold_Pass", "Top10", "Top10_Pass",
                "Snipers", "Snipers_Pass", "Bundles", "Bundles_Pass", "Insiders", "Insiders_Pass",
                "KOLs", "Kols_Pass", "BondingCurve", "BCPass", "Overall_Pass", 
                "OriginalMC", "CurrentMC", "GrowthRatio"  # Removed MarketCap
            ])
            writer.writerows(rows)
    logger.info(f"{'Updated' if updated else 'Logged'} filter results to {csv_file} for CA: {ca}")

# Log growth check results to CSV
def log_to_growthcheck_csv(chat_id, channel_id, message_id, token_name, ca, original_mc, current_mc,
                           growth_ratio, profit_percent, time_since_added, is_vip_channel):
    if channel_id not in VIP_CHANNEL_IDS and channel_id not in PUBLIC_CHANNEL_IDS:
        logger.debug(f"Skipping growth log for CA {ca} in channel {channel_id} (not VIP or Public)")
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    csv_file = VIP_GROWTH_CSV_FILE if is_vip_channel else PUBLIC_GROWTH_CSV_FILE
    with growth_csv_lock:
        rows = []
        updated = False
        if os.path.exists(csv_file):
            with open(csv_file, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                for row in reader:
                    if row["CA"] == ca and row["MessageID"] == str(message_id):
                        rows.append([
                            timestamp, chat_id, channel_id, message_id, token_name, ca,
                            original_mc, current_mc, growth_ratio, profit_percent, time_since_added
                        ])
                        updated = True
                    else:
                        rows.append(list(row.values()))
        if not updated:
            rows.append([
                timestamp, chat_id, channel_id, message_id, token_name, ca,
                original_mc, current_mc, growth_ratio, profit_percent, time_since_added
            ])
        with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "ChatID", "ChannelID", "MessageID", "TokenName", "CA",
                "OriginalMC", "CurrentMC", "GrowthRatio", "ProfitPercent", "TimeSinceAdded"
            ])
            writer.writerows(rows)
    logger.info(f"{'Updated' if updated else 'Logged'} growth check to {csv_file} for CA: {ca}")

# Helper to fetch latest growth ratio from VIP growth CSV
def get_latest_growth_ratio(ca):
    if not os.path.exists(VIP_GROWTH_CSV_FILE):
        return None
    with open(VIP_GROWTH_CSV_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        latest_ratio = None
        latest_timestamp = None
        for row in reader:
            if row["CA"] == ca:
                row_time = datetime.strptime(row["Timestamp"], "%Y-%m-%d %H:%M:%S")
                if latest_timestamp is None or row_time > latest_timestamp:
                    latest_timestamp = row_time
                    latest_ratio = float(row["GrowthRatio"])
        return latest_ratio

# Helper function to parse market cap
def parse_market_cap(mc_str):
    if not mc_str:
        return None
    mc_str = mc_str.replace('$', '').replace(',', '').strip()
    try:
        if 'k' in mc_str.lower():
            return float(mc_str.lower().replace('k', '')) * 1000
        elif 'm' in mc_str.lower():
            return float(mc_str.lower().replace('m', '')) * 1000000
        else:
            return float(mc_str)
    except ValueError as e:
        logger.error(f"Failed to parse market cap '{mc_str}': {str(e)}")
        return None
"""
# Helper function to calculate time since a timestamp
def calculate_time_since(timestamp):
    current_time = time.time()
    seconds = int(current_time - timestamp)
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h"
    days = hours // 24
    return f"{days}d"
"""

# Handler for /adduser command
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
        await message.answer("⚠️ An additional user has already been added.")
        logger.info("Additional user already added, rejecting new addition")
        return

    text = message.text.lower().replace('/adduser', '').strip()
    if not text:
        await message.answer("Please provide a username (e.g., /adduser @NewUser) 🤔")
        return

    new_user = text if text.startswith('@') else f"@{text}"
    if new_user == "@BeingHumbleGuy":
        await message.answer("⚠️ @BeingHumbleGuy is already the super user.")
        return

    authorized_users.append(new_user)
    additional_user_added = True
    await message.answer(f"Authorized user added: {new_user} ✅")
    logger.info(f"Authorized user added: {new_user}")
    
    
#Chunk 1 ends

import cloudscraper
import json
import time
import asyncio
import logging
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class APISessionManager:
    def __init__(self):
        self.session = None
        self._session_created_at = 0
        self._session_requests = 0
        self._session_max_age = 3600  # 1 hour
        self._session_max_requests = 100
        self.max_retries = 5
        self.retry_delay = 2  # 2 seconds to mitigate rate-limiting
        self.base_url = "https://gmgn.ai/defi/quotation/v1/tokens/sol"  # Updated to Link Bot endpoint
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.ua = UserAgent()

        self.headers_dict = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate",  # Removed 'br' to avoid Brotli issues
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Origin": "https://gmgn.ai",
            "Referer": "https://gmgn.ai/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        self.proxy_list = [
            {
                "host": "residential.birdproxies.com",
                "port": 7777,
                "username": "pool-p1-cc-us",
                "password": "sf3lefz1yj3zwjvy"
            } for _ in range(50)
        ]
        self.current_proxy_index = 0
        logger.info(f"Initialized proxy list with {len(self.proxy_list)} proxies")

    async def get_proxy(self):
        if not self.proxy_list:
            logger.warning("No proxies available in the proxy list")
            return None
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
        logger.debug(f"Selected proxy: {proxy_url}")
        return {"http": proxy_url, "https": proxy_url}

    def update_proxy_list(self, proxy: dict, append: bool = True):
        required_keys = {"host", "port", "username", "password"}
        if not all(key in proxy for key in required_keys):
            logger.error(f"Invalid proxy format: {proxy}. Expected {required_keys}")
            return False

        formatted_proxy = {
            "host": proxy["host"],
            "port": proxy["port"],
            "username": proxy["username"],
            "password": proxy["password"]
        }
        if append:
            if formatted_proxy not in self.proxy_list:
                self.proxy_list.append(formatted_proxy)
                logger.info(f"Appended proxy: {formatted_proxy}")
            else:
                logger.info(f"Proxy already exists: {formatted_proxy}")
        else:
            self.proxy_list = [formatted_proxy]
            self.current_proxy_index = 0
            logger.info(f"Replaced proxy list with: {formatted_proxy}")
        return True

    def clear_proxy_list(self):
        self.proxy_list = []
        self.current_proxy_index = 0
        logger.info("Cleared proxy list")

    async def randomize_session(self, force: bool = False, use_proxy: bool = True):
        current_time = time.time()
        session_expired = (current_time - self._session_created_at) > self._session_max_age
        too_many_requests = self._session_requests >= self._session_max_requests
        
        if self.session is None or force or session_expired or too_many_requests:
            self.session = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                }
            )
            user_agent = self.ua.random
            self.headers_dict["User-Agent"] = user_agent
            self.session.headers.update(self.headers_dict)
            logger.debug(f"Randomized User-Agent: {user_agent}")
            
            if use_proxy and self.proxy_list:
                proxy_dict = await self.get_proxy()
                if proxy_dict:
                    self.session.proxies = proxy_dict
                    logger.debug(f"Successfully configured proxy {proxy_dict}")
                else:
                    logger.warning("No proxy available, proceeding without proxy.")
            else:
                self.session.proxies = None
                logger.debug("Proceeding without proxy as per request.")
            
            self._session_created_at = current_time
            self._session_requests = 0
            logger.debug("Created new cloudscraper session")

    async def _run_in_executor(self, func, *args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(
            self._executor, 
            lambda: func(*args, **kwargs)
        )

    async def fetch_token_data(self, mint_address):
        logger.debug(f"Fetching data for mint_address: {mint_address}")
        await self.randomize_session()
        if not self.session:
            logger.error("Cloudscraper session not initialized")
            return {"error": "Cloudscraper session not initialized"}

        self._session_requests += 1
        url = f"{self.base_url}/{mint_address}"  # Updated URL construction

        for attempt in range(self.max_retries):
            try:
                response = await self._run_in_executor(
                    self.session.get,
                    url,
                    headers=self.headers_dict,
                    timeout=15
                )
                headers_log = {k: v for k, v in response.headers.items()}
                logger.debug(f"Attempt {attempt + 1} for CA {mint_address} - Status: {response.status_code}, Response length: {len(response.text)}, Headers: {headers_log}")

                if response.status_code != 200:
                    if response.status_code == 403:
                        logger.warning(f"Attempt {attempt + 1} for CA {mint_address} failed with 403: {response.text[:100]}, Headers: {headers_log}")
                        if "Just a moment" in response.text:
                            logger.warning(f"Cloudflare challenge detected for CA {mint_address}, rotating proxy")
                            await self.randomize_session(force=True, use_proxy=True)
                    elif response.status_code == 429:
                        logger.warning(f"Attempt {attempt + 1} for CA {mint_address} failed with 429: Rate limited, Headers: {headers_log}")
                        delay = self.retry_delay * (2 ** attempt) * 2
                        logger.debug(f"Backing off for {delay}s before retry {attempt + 2} for CA {mint_address}")
                        await asyncio.sleep(delay)
                    else:
                        logger.warning(f"Attempt {attempt + 1} for CA {mint_address} failed with status {response.status_code}: {response.text[:100]}, Headers: {headers_log}")
                    if attempt == self.max_retries - 1:
                        break
                    delay = self.retry_delay * (2 ** attempt)
                    logger.debug(f"Backing off for {delay}s before retry {attempt + 2} for CA {mint_address}")
                    await asyncio.sleep(delay)
                    continue

                content_type = response.headers.get('Content-Type', '')
                if 'application/json' not in content_type.lower():
                    logger.warning(f"Non-JSON response for CA {mint_address}: Content-Type={content_type}, Response: {response.text[:500]}")
                    await self.randomize_session(force=True, use_proxy=True)
                    return {"error": f"Unexpected Content-Type: {content_type}"}

                content_length = int(response.headers.get('Content-Length', -1))
                if content_length == 0 or not response.text.strip():
                    logger.error(f"Empty response for CA {mint_address}: Content-Length={content_length}, Response: {response.text[:500]}")
                    await self.randomize_session(force=True, use_proxy=True)
                    return {"error": "Empty response from API"}

                try:
                    json_data = response.json()
                    logger.debug(f"Raw response for CA {mint_address} (first 500 chars): {response.text[:500]}")
                    json_data["headers"] = headers_log

                    if "address" in json_data or ("data" in json_data and isinstance(json_data.get("data"), dict) and "tokens" in json_data["data"]):
                        return json_data
                    elif "code" in json_data and json_data.get("code") != 0:
                        logger.error(f"API error for CA {mint_address}: code={json_data.get('code')}, msg={json_data.get('msg')}")
                        return {"error": f"API error: code={json_data.get('code')}, msg={json_data.get('msg')}"}
                    else:
                        logger.error(f"Unexpected response structure for CA {mint_address}: {response.text[:500]}")
                        return {"error": f"Unexpected response structure for CA {mint_address}"}

                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error for CA {mint_address}: {str(e)}, Response: {response.text[:500]}, Headers: {headers_log}")
                    if attempt < self.max_retries - 1:
                        logger.debug(f"Retrying due to JSON decode error for CA {mint_address}")
                        delay = self.retry_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    return {"error": f"Invalid JSON response for CA {mint_address}: {str(e)}"}

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} for CA {mint_address} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.debug(f"Backing off for {delay}s before retry {attempt + 2} for CA {mint_address}")
                    await asyncio.sleep(delay)

        logger.info(f"All proxy attempts failed for CA {mint_address}, trying without proxy")
        await self.randomize_session(force=True, use_proxy=False)
        try:
            response = await self._run_in_executor(
                self.session.get,
                url,
                headers=self.headers_dict,
                timeout=15
            )
            headers_log = {k: v for k, v in response.headers.items()}
            logger.debug(f"Fallback for CA {mint_address} - Status: {response.status_code}, Response length: {len(response.text)}, Headers: {headers_log}")

            if response.status_code != 200:
                logger.warning(f"Fallback for CA {mint_address} failed with status {response.status_code}: {response.text[:100]}, Headers: {headers_log}")
                return {"error": f"Fallback failed for CA {mint_address}: HTTP {response.status_code}"}

            content_type = response.headers.get('Content-Type', '')
            if 'application/json' not in content_type.lower():
                logger.warning(f"Fallback non-JSON response for CA {mint_address}: Content-Type={content_type}, Response: {response.text[:500]}")
                return {"error": f"Unexpected Content-Type: {content_type}"}

            content_length = int(response.headers.get('Content-Length', -1))
            if content_length == 0 or not response.text.strip():
                logger.error(f"Fallback empty response for CA {mint_address}: Content-Length={content_length}, Response: {response.text[:500]}")
                return {"error": "Empty response from API"}

            try:
                json_data = response.json()
                logger.debug(f"Fallback raw response for CA {mint_address} (first 500 chars): {response.text[:500]}")
                json_data["headers"] = headers_log

                if "address" in json_data or ("data" in json_data and isinstance(json_data.get("data"), dict) and "tokens" in json_data["data"]):
                    return json_data
                elif "code" in json_data and json_data.get("code") != 0:
                    logger.error(f"Fallback API error for CA {mint_address}: code={json_data.get('code')}, msg={json_data.get('msg')}")
                    return {"error": f"API error: code={json_data.get('code')}, msg={json_data.get('msg')}"}
                else:
                    logger.error(f"Fallback unexpected response structure for CA {mint_address}: {response.text[:500]}")
                    return {"error": f"Unexpected response structure for CA {mint_address}"}

            except json.JSONDecodeError as e:
                logger.error(f"Fallback JSON decode error for CA {mint_address}: {str(e)}, Response: {response.text[:500]}, Headers: {headers_log}")
                return {"error": f"Invalid JSON response for CA {mint_address}: {str(e)}"}

        except Exception as e:
            logger.error(f"Final attempt without proxy failed for CA {mint_address}: {str(e)}")
            return {"error": f"Failed to fetch data for CA {mint_address}: {str(e)}"}

        logger.error(f"Failed to fetch data for CA {mint_address} after {self.max_retries} attempts")
        return {"error": f"Failed to fetch data for CA {mint_address} after retries"}

api_session_manager = APISessionManager()

def format_market_cap(market_cap: float) -> str:
    if market_cap >= 1_000_000:
        return f"{market_cap / 1_000_000:.2f}M"
    elif market_cap >= 1_000:
        return f"{market_cap / 1_000:.2f}K"
    elif market_cap > 0:
        return f"{market_cap:.2f}"
    return "N/A"

async def get_gmgn_token_data(mint_address):
    if mint_address in token_data_cache:
        logger.info(f"Returning cached data for CA: {mint_address}")
        return token_data_cache[mint_address]

    token_data_raw = await api_session_manager.fetch_token_data(mint_address)
    logger.debug(f"Received raw token data for CA {mint_address}: {token_data_raw}")
    if "error" in token_data_raw:
        logger.error(f"Error from fetch_token_data for CA {mint_address}: {token_data_raw['error']}")
        return {"error": token_data_raw["error"]}

    try:
        # Handle Cloudflare challenge indicators
        if "cf-ray" in token_data_raw.get("headers", {}):
            logger.info(f"Cloudflare headers detected for CA {mint_address}, possible CAPTCHA challenge")

        # Check if response is a single token object or wrapped in 'data' with 'tokens' list
        token_info = None
        if isinstance(token_data_raw, dict) and "data" in token_data_raw and isinstance(token_data_raw.get("data"), dict) and "tokens" in token_data_raw["data"]:
            if not isinstance(token_data_raw["data"]["tokens"], list):
                logger.warning(f"Invalid 'tokens' key in response for CA {mint_address}: {token_data_raw}")
                return {"error": f"No valid token data returned from API for CA {mint_address}"}
            if len(token_data_raw["data"]["tokens"]) == 0:
                logger.warning(f"No tokens found in API response for CA {mint_address}: {token_data_raw}")
                return {"error": f"Token not found for CA {mint_address} on gmgn.ai. Please verify the contract address."}
            token_info = token_data_raw["data"]["tokens"][0]
        elif isinstance(token_data_raw, dict) and "address" in token_data_raw:
            token_info = token_data_raw  # Direct token object
        else:
            logger.warning(f"Invalid response structure for CA {mint_address}: {token_data_raw}")
            return {"error": f"Invalid API response for CA {mint_address}: expected token object or tokens list"}

        logger.debug(f"Token info for CA {mint_address}: {token_info}")
        
        token_data = {}
        price = float(token_info.get("price", 0))
        token_data["price"] = str(price) if price != 0 else "N/A"
        logger.debug(f"Token Price for CA {mint_address}: {str(price)}")
        token_data["price_1h"] = float(token_info.get("price_1h", 0))
        token_data["price_24h"] = float(token_info.get("price_24h", 0))
        total_supply = float(token_info.get("total_supply", 0))
        token_data["circulating_supply"] = total_supply
        token_data["market_cap"] = price * total_supply
        token_data["market_cap_str"] = format_market_cap(token_data["market_cap"])
        token_data["liquidity"] = float(token_info.get("liquidity", 0))
        token_data["liquidity_str"] = format_market_cap(token_data["liquidity"])
        token_data["volume_24h"] = float(token_info.get("volume_24h", 0))
        token_data["swaps_24h"] = token_info.get("swaps_24h", 0)
        token_data["top_10_holder_rate"] = float(token_info.get("top_10_holder_rate", 0)) * 100
        token_data["renounced_mint"] = bool(token_info.get("renounced_mint", False))
        token_data["renounced_freeze_account"] = bool(token_info.get("renounced_freeze_account", False))
        token_data["contract"] = mint_address
        token_data["name"] = token_info.get("name", "Unknown")
        token_data["symbol"] = token_info.get("symbol", "")
        token_data["hot_level"] = int(token_info.get("hot_level", 0))

        logger.debug(f"Processed token data for CA {mint_address}: market_cap={token_data['market_cap']:.2f}, symbol={token_data['symbol']}, hot_level={token_data['hot_level']}")
        token_data_cache[mint_address] = token_data
        logger.info(f"Cached token data for CA: {mint_address}")
        return token_data

    except Exception as e:
        logger.error(f"Error processing API response for CA {mint_address}: {str(e)}, Raw response: {token_data_raw}")
        return {"error": f"Failed to process API response for CA {mint_address}: {str(e)}"}

async def get_token_market_cap(mint_address):
    token_data_raw = await api_session_manager.fetch_token_data(mint_address)
    logger.debug(f"Received raw market cap data for CA {mint_address}: {token_data_raw}")
    if "error" in token_data_raw:
        logger.error(f"Error from fetch_token_data for CA {mint_address}: {token_data_raw['error']}")
        return {"market_cap": 0}

    try:
        token_info = None
        if isinstance(token_data_raw, dict) and "data" in token_data_raw and isinstance(token_data_raw.get("data"), dict) and "tokens" in token_data_raw["data"]:
            if not isinstance(token_data_raw["data"]["tokens"], list):
                logger.warning(f"Invalid 'tokens' key in response for CA {mint_address}: {token_data_raw}")
                return {"market_cap": 0}
            if len(token_data_raw["data"]["tokens"]) == 0:
                logger.warning(f"No tokens found in API response for CA {mint_address}: {token_data_raw}")
                return {"market_cap": 0}
            token_info = token_data_raw["data"]["tokens"][0]
        elif isinstance(token_data_raw, dict) and "address" in token_data_raw:
            token_info = token_data_raw
        else:
            logger.warning(f"Invalid response structure for CA {mint_address}: {token_data_raw}")
            return {"market_cap": 0}

        price = float(token_info.get("price", 0))
        total_supply = float(token_info.get("total_supply", 0))
        market_cap = price * total_supply
        return {"market_cap": market_cap}
    except Exception as e:
        logger.error(f"Error fetching market cap for CA {mint_address}: {str(e)}")
        return {"market_cap": 0}

# Chunk 2 ends

# Chunk 3 starts
# Chunk 3a starts
from aiogram import types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, MessageEntity
from aiogram import F
import re

VIP_CHANNEL_IDS = {-1002365061913}
PUBLIC_CHANNEL_IDS = {-1002272066154}

async def process_message(message: types.Message) -> None:
    if not message.text:
        logger.debug("Message has no text, skipping")
        return

    bot_info = await bot.get_me()
    if message.from_user and message.from_user.id == bot_info.id:
        logger.debug("Message is from the bot itself, skipping")
        return

    text = message.text  # Original message text
    chat_id = message.chat.id
    message_id = message.message_id

    ca_match = re.search(r'[A-Za-z0-9]{44}', text)
    if not ca_match:
        logger.debug("No CA found in message, skipping")
        return
    ca = ca_match.group(0)

    has_early = "early" in text.lower()
    has_fasol = "fasol" in text.lower()  # Check original text for "Fasol"
    if not (has_early or has_fasol):
        logger.debug("No 'Early' or 'Fasol' keywords found, skipping")
        return

    logger.info(f"Handler triggered for message: '{text}' (chat_id={chat_id}, type={message.chat.type}, message_id={message_id})")
    logger.debug(f"Extracted CA: {ca}")
    logger.debug(f"Keyword check - Has Early: {has_early}, Has Fasol: {has_fasol}")

    is_vip_channel = chat_id in VIP_CHANNEL_IDS
    is_public_channel = chat_id in PUBLIC_CHANNEL_IDS
    
    mc_match = re.search(r'(?:💎\s*(?:MC|C)|Cap):\s*\$?(\d+\.?\d*[KM]?)', text, re.IGNORECASE)
    original_mc = 0
    if mc_match:
        mc_str = mc_match.group(1)
        try:
            original_mc = parse_market_cap(mc_str)
            logger.debug(f"Parsed market cap: {original_mc}")
        except ValueError as e:
            logger.error(f"Failed to parse market cap '{mc_str}': {str(e)}")

    if has_fasol:
        logger.info(f"Processing 'Fasol' message in chat {chat_id} (type: {message.chat.type})")
        ca_index = text.find(ca)
        if ca_index != -1:
            details = text[:ca_index].strip()
        else:
            details = text.split('\n')[:5]
            details = '\n'.join(details).strip()

        # Extract token symbol (assumes format like "$SYMBOL" at the start of details)
        token_symbol_match = re.search(r'\$[A-Za-z0-9]+', details)
        token_symbol = token_symbol_match.group(0) if token_symbol_match else "$Unknown"
        
        # Create hyperlink for token symbol to pump.fun
        pump_fun_url = f"https://pump.fun/coin/{ca}"
        hyperlinked_symbol = f"[{token_symbol}]({pump_fun_url})"
        
        # Replace the plain token symbol in details with the hyperlinked version
        if token_symbol_match:
            details = details.replace(token_symbol, hyperlinked_symbol)
        
        # output_text = f"{details}\n🔗 CA: {ca}"  # New text without "Fasol"
        output_text = f"{details}\n🔗 CA: `{ca}`"  # New text without "Fasol"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            # [InlineKeyboardButton(text="🌟🚀 Join VIP 🚀🌟", url="https://t.me/HumbleMoonshotsPay_bot?start=start")]
            # [InlineKeyboardButton(text="👉🔥 JOIN VIP NOW 🔥👉", url="https://t.me/HumbleMoonshotsPay_bot?start=start")]
            # if not is_vip_channel else [],
            [
                InlineKeyboardButton(text="Fasol", url=f"https://t.me/fasol_robot?start=ref_humbleguy_ca_{ca}"),
                InlineKeyboardButton(text="Bloom", url=f"https://t.me/BloomSolana_bot?start=ref_humbleguy_ca_{ca}")
            ],
            #[
            #    InlineKeyboardButton(text="Maestro", url=f"http://t.me/maestro?start={ca}-beinghumbleguy"),
            #    InlineKeyboardButton(text="Trojan", url=f"https://t.me/solana_trojanbot?start=r-beinghumbleguy-{ca}")
            #],
            [
                 InlineKeyboardButton(text="👉 Claim 0.1 SOL in Fasol Bot 👉", url="https://t.me/fasol_robot?start=ref_humbleguy")
            #    InlineKeyboardButton(text="Photon", url=f"https://photon-sol.tinyastro.io/en/r/@humbleguy/{ca}"),
                 # InlineKeyboardButton(text="Trojan", url=f"https://t.me/solana_trojanbot?start=r-beinghumbleguy-{ca}"),
                 # InlineKeyboardButton(text="Axiom", url=f"https://axiom.trade/t/{ca}/@humbleguy")
            ],
            
            [InlineKeyboardButton(text="👉🔥 JOIN VIP NOW 🔥👉", url="https://t.me/HumbleMoonshotsPay_bot?start=start")] if not is_vip_channel else []
        ])

        # Growth monitoring happens BEFORE editing
        if is_vip_channel or is_public_channel:
            first_line = text.split('\n')[0].strip()  # From original text
            key = f"{ca}:{chat_id}"
            monitored_tokens[key] = {
                "token_name": first_line,
                "initial_mc": original_mc,
                "peak_mc": original_mc,
                "timestamp": datetime.now(pytz.timezone('America/New_York')).timestamp(),
                "message_id": message_id,
                "chat_id": chat_id
            }
            logger.debug(f"Added CA {ca} to monitored_tokens with key {key} for growth tracking (Fasol)")
            save_monitored_tokens()
        else:
            logger.debug(f"CA {ca} not added to monitored_tokens (not in VIP or Public channel)")

        # Log initial filter data BEFORE editing
        growth_ratio = get_latest_growth_ratio(ca)
        log_to_csv(
            ca=ca,
            token_name=text.split('\n')[0].strip(),
            bs_ratio=None,
            bs_ratio_pass=None,
            check_low_pass=None,
            dev_sold=None,
            dev_sold_left_value=None,
            dev_sold_pass=None,
            top_10=None,
            top_10_pass=None,
            snipers=None,
            snipers_pass=None,
            bundles=None,
            bundles_pass=None,
            insiders=None,
            insiders_pass=None,
            kols=None,
            kols_pass=None,
            bonding_curve=None,
            bc_pass=None,
            overall_pass=None,
            original_mc=original_mc,
            current_mc=original_mc,
            growth_ratio=growth_ratio,
            is_vip_channel=is_vip_channel
        )

        # Edit message LAST
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=output_text,
                reply_markup=keyboard,
                parse_mode="Markdown",
                disable_web_page_preview=False  # Enable link previews
            )
            logger.info(f"Edited original message with trading buttons for CA {ca} in chat {chat_id}")
        except Exception as e:
            logger.warning(f"Failed to edit message {message_id} in chat {chat_id}: {e}")
            try:
                if message.chat.type == "channel":
                    final_msg = await bot.send_message(
                        chat_id=chat_id,
                        text=output_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown",
                        disable_web_page_preview=False  # Enable link previews
                    )
                else:
                    final_msg = await message.reply(
                        text=output_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown",
                        reply_to_message_id=message_id,
                        disable_web_page_preview=False  # Enable link previews
                    )
                logger.info(f"Posted new message with trading buttons for CA {ca} in chat {chat_id} (edit failed)")
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    logger.info(f"Deleted original message {message_id} in chat {chat_id}")
                except Exception as del_e:
                    logger.warning(f"Failed to delete original message {message_id} in chat {chat_id}: {del_e}")
            except Exception as post_e:
                logger.error(f"Failed to post fallback message for CA {ca}: {post_e}")
                return
        return

# Chunk 3a ends
# Chunk 3b starts
    if not has_early:
        logger.debug("No 'Early' keyword found, skipping filter logic")
        return

    logger.info(f"Processing 'Early' message in chat {chat_id} (type: {message.chat.type})")
    buy_percent = 0
    sell_percent = 0
    dev_sold = "N/A"
    dev_sold_left_value = None
    top_10 = 0
    snipers = 0
    bundles = 0
    insiders = 0
    kols = 0
    bonding_curve = 0

    logger.debug(f"Full message text being searched: '{text}'")

    buy_sell_matches = re.findall(r'Sum\s*🅑\s*:\s*(\d+\.?\d*)%\s*(?:\|\s*Sum\s*🅢\s*:\s*(\d+\.?\d*)%)?', text)
    if buy_sell_matches:
        last_match = buy_sell_matches[-1]
        buy_percent = float(last_match[0])
        sell_percent = float(last_match[1]) if last_match[1] else 0
        logger.debug(f"Extracted Buy: {buy_percent}%, Sell: {sell_percent}% from last match: {last_match}")
    else:
        logger.warning(f"Failed to extract Buy/Sell percentages from: '{text}'")

    dev_sold_match = re.search(r'Dev:(✅|❌)\s*(?:\((\d+\.?\d*)%\s*left\))?', text)
    if dev_sold_match:
        dev_sold = "Yes" if dev_sold_match.group(1) == "✅" else "No"
        if dev_sold_match.group(2):
            dev_sold_left_value = float(dev_sold_match.group(2))

    top_10_match = re.search(r'Top 10:\s*(\d+\.?\d*)%', text)
    if top_10_match:
        top_10 = float(top_10_match.group(1))

    snipers_match = re.search(r'Sniper:\s*\d+\s*buy\s*(\d+\.?\d*)%', text)
    if snipers_match:
        snipers = float(snipers_match.group(1))

    bundles_match = re.search(r'Bundle:\s*\d+\s*buy\s*(\d+\.?\d*)%', text)
    if bundles_match:
        bundles = float(bundles_match.group(1))

    insiders_match = re.search(r'🐁Insiders:\s*(\d+)', text)
    if insiders_match:
        insiders = int(insiders_match.group(1))

    kols_match = re.search(r'🌟KOLs:\s*(\d+)', text)
    if kols_match:
        kols = int(kols_match.group(1))

    bc_match = re.search(r'Bonding Curve:\s+(\d+\.?\d*)%', text)
    if bc_match:
        bonding_curve = float(bc_match.group(1))
        logger.debug(f"Extracted Bonding Curve: {bonding_curve}%")
    else:
        logger.warning(f"Failed to extract Bonding Curve from: '{text}'")

    all_filters_pass = False
    filter_results = []

    if buy_percent != 0 and sell_percent != 0:
        bs_ratio = buy_percent / sell_percent
    else:
        bs_ratio = float('inf') if buy_percent > 0 else 0
    logger.debug(f"Calculated BSRatio: {bs_ratio} (Buy: {buy_percent}, Sell: {sell_percent})")
    bs_ratio_pass = False
    if CheckHighEnabled and bs_ratio >= PassValue:
        bs_ratio_pass = True
    elif CheckLowEnabled and 1 <= bs_ratio <= RangeLow:
        bs_ratio_pass = True
    filter_results.append(f"BSRatio: {bs_ratio:.2f} {'✅' if bs_ratio_pass else '🚫'} (Threshold: >= {PassValue} or 1 to {RangeLow})")

    dev_sold_pass = False
    if not DevSoldFilterEnabled:
        filter_results.append(f"DevSold: {dev_sold} (Disabled)")
    else:
        if dev_sold == DevSoldThreshold:
            dev_sold_pass = True
            filter_results.append(f"DevSold: {dev_sold} ✅ (Passes because DevSold is {DevSoldThreshold})")
        elif dev_sold == "No" and dev_sold_left_value is not None and dev_sold_left_value <= DevSoldLeft:
            dev_sold_pass = True
            filter_results.append(f"DevSold: {dev_sold} ({dev_sold_left_value}% left) ✅ (Threshold: {DevSoldThreshold}, Left <= {DevSoldLeft}%)")
        else:
            filter_results.append(f"DevSold: {dev_sold} {'🚫' if dev_sold_left_value is None else f'({dev_sold_left_value}% left) 🚫'} (Threshold: {DevSoldThreshold}, Left <= {DevSoldLeft}%)")

    top_10_pass = False
    if not Top10FilterEnabled:
        filter_results.append(f"Top10: {top_10} (Disabled)")
    else:
        top_10_pass = top_10 <= Top10Threshold
        filter_results.append(f"Top10: {top_10} {'✅' if top_10_pass else '🚫'} (Threshold: <= {Top10Threshold})")

    if not SniphersFilterEnabled or SnipersThreshold is None:
        filter_results.append(f"Snipers: {snipers} (Disabled)")
        snipers_pass = True
    else:
        snipers_pass = snipers <= SnipersThreshold
        filter_results.append(f"Snipers: {snipers} {'✅' if snipers_pass else '🚫'} (Threshold: <= {SnipersThreshold})")

    if not BundlesFilterEnabled:
        filter_results.append(f"Bundles: {bundles} (Disabled)")
        bundles_pass = True
    else:
        bundles_pass = bundles <= BundlesThreshold
        filter_results.append(f"Bundles: {bundles} {'✅' if bundles_pass else '🚫'} (Threshold: <= {BundlesThreshold})")

    if not InsidersFilterEnabled or InsidersThreshold is None:
        filter_results.append(f"Insiders: {insiders} (Disabled)")
        insiders_pass = True
    else:
        insiders_pass = insiders <= InsidersThreshold
        filter_results.append(f"Insiders: {insiders} {'✅' if insiders_pass else '🚫'} (Threshold: <= {InsidersThreshold})")

    if not KOLsFilterEnabled:
        filter_results.append(f"KOLs: {kols} (Disabled)")
        kols_pass = True
    else:
        kols_pass = kols >= KOLsThreshold
        filter_results.append(f"KOLs: {kols} {'✅' if kols_pass else '🚫'} (Threshold: >= {KOLsThreshold})")

    if not BondingCurveFilterEnabled:
        filter_results.append(f"BondingCurve: {bonding_curve} (Disabled)")
        bc_pass = True
    else:
        bc_pass = bonding_curve >= BondingCurveThreshold
        filter_results.append(f"BondingCurve: {bonding_curve} {'✅' if bc_pass else '🚫'} (Threshold: >= {BondingCurveThreshold})")

    all_filters_pass = all([
        bs_ratio_pass,
        dev_sold_pass if DevSoldFilterEnabled else True,
        top_10_pass if Top10FilterEnabled else True,
        snipers_pass if SniphersFilterEnabled and SnipersThreshold is not None else True,
        bundles_pass if BundlesFilterEnabled else True,
        insiders_pass if InsidersFilterEnabled and InsidersThreshold is not None else True,
        kols_pass if KOLsFilterEnabled else True,
        bc_pass if BondingCurveFilterEnabled else True
    ])

    first_line = text.split('\n')[0].strip()
    growth_ratio = get_latest_growth_ratio(ca)
    log_to_csv(
        ca=ca,
        token_name=first_line,
        bs_ratio=bs_ratio,
        bs_ratio_pass=bs_ratio_pass,
        check_low_pass=None,
        dev_sold=dev_sold,
        dev_sold_left_value=dev_sold_left_value,
        dev_sold_pass=dev_sold_pass,
        top_10=top_10,
        top_10_pass=top_10_pass,
        snipers=snipers,
        snipers_pass=snipers_pass if SniphersFilterEnabled and SnipersThreshold is not None else None,
        bundles=bundles,
        bundles_pass=bundles_pass if BundlesFilterEnabled else None,
        insiders=insiders,
        insiders_pass=insiders_pass if InsidersFilterEnabled and InsidersThreshold is not None else None,
        kols=kols,
        kols_pass=kols_pass if KOLsFilterEnabled else None,
        bonding_curve=bonding_curve,
        bc_pass=bc_pass if BondingCurveFilterEnabled else None,
        overall_pass=all_filters_pass,
        original_mc=original_mc,
        current_mc=original_mc,
        growth_ratio=growth_ratio,
        is_vip_channel=is_vip_channel
    )

    output_text = f"{'CA qualified: ✅' if all_filters_pass else 'CA did not qualify: 🚫'}\n**{first_line}**\n**🔗 CA: {ca}**\n" + "\n".join(filter_results)

    try:
        if message.chat.type == "channel":
            await bot.send_message(chat_id=chat_id, text=output_text, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            await message.reply(
                text=output_text,
                parse_mode="Markdown",
                reply_to_message_id=message_id,
                entities=[MessageEntity(type="code", offset=output_text.index(ca), length=len(ca))]
            )
        logger.info(f"Filter results sent for CA {ca} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send filter results for CA {ca}: {str(e)}")
    # No growth monitoring for "Early" CAs

@dp.message(~Command(commands=[
    "test", "ca", "setfilter", "setpassvalue", "setrangelow", "setcheckhigh", 
    "setchecklow", "setdevsoldthreshold", "setdevsoldleft", "setdevsoldfilter", 
    "settop10threshold", "settop10filter", "setsnipersthreshold", "setsnipersfilter", 
    "setbundlesthreshold", "setbundlesfilter", "setinsidersthreshold", "setinsidersfilter", 
    "setkolsthreshold", "setkolsfilter", "adduser", "downloadcsv", "downloadgrowthcsv", 
    "growthnotify", "mastersetup", "resetdefaults",
    "setbcthreshold", "setbcfilter","setpnlreport","testtweet","runpnlreport","getchatid","downloadmonitoredtokens"
]), F.text)
async def handle_message(message: types.Message) -> None:
    await process_message(message)

@dp.channel_post(F.text)
async def handle_channel_post(message: types.Message) -> None:
    await process_message(message)

# Chunk 3b ends
# Chunk 3 ends

# Chunk 4 starts
def calculate_time_since(timestamp):
    current_time = datetime.now(pytz.timezone('America/New_York'))
    token_time = datetime.fromtimestamp(timestamp, pytz.timezone('America/New_York'))
    diff_seconds = int((current_time - token_time).total_seconds())
    if diff_seconds < 60:
        return f"{diff_seconds}s"
    minutes = diff_seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    remaining_minutes = minutes % 60
    return f"{hours}h:{remaining_minutes:02d}m"

async def growthcheck() -> None:
    current_time = datetime.now(pytz.timezone('America/New_York'))
    to_remove = []
    peak_updates = {}
    # Move notified_cas to module-level to persist across calls for Telegram
    if not hasattr(growthcheck, 'notified_cas'):
        growthcheck.notified_cas = set()  # For Telegram 2.3x+ notifications
    notified_cas = growthcheck.notified_cas
    # New set for Twitter notifications to avoid interference and track first 3x
    if not hasattr(growthcheck, 'notified_cas_twitter'):
        growthcheck.notified_cas_twitter = set()
    notified_cas_twitter = growthcheck.notified_cas_twitter
    logger.debug(f"Starting growthcheck with monitored_tokens: {len(monitored_tokens)} tokens")

    # Group tokens by CA for cross-channel comparison
    tokens_by_ca = {}
    for key in list(monitored_tokens.keys()):
        ca, chat_id = key.split(':')
        chat_id = int(chat_id)
        if ca not in tokens_by_ca:
            tokens_by_ca[ca] = {}
        tokens_by_ca[ca][chat_id] = monitored_tokens[key]

    for ca, channel_data in tokens_by_ca.items():
        token_data = await get_token_market_cap(ca)
        if "error" in token_data:
            logger.debug(f"Skipping CA {ca} due to API error: {token_data['error']}")
            continue
        current_mc = token_data["market_cap"]
        if current_mc is None or current_mc == 0:
            logger.debug(f"Skipping CA {ca} due to invalid current_mc: {current_mc}")
            continue

        # Process each channel (VIP and Public) independently
        vip_chat_id = list(VIP_CHANNEL_IDS)[0] if VIP_CHANNEL_IDS else None
        public_chat_id = list(PUBLIC_CHANNEL_IDS)[0] if PUBLIC_CHANNEL_IDS else None

        vip_data = channel_data.get(vip_chat_id) if vip_chat_id else None
        public_data = channel_data.get(public_chat_id) if public_chat_id else None

        # Calculate growth ratios
        vip_growth_ratio = None
        public_growth_ratio = None

        if vip_data:
            vip_initial_mc = vip_data["initial_mc"]
            vip_growth_ratio = current_mc / vip_initial_mc if vip_initial_mc != 0 else 0
            if current_mc > vip_data.get("peak_mc", vip_initial_mc):
                peak_updates[f"{ca}:{vip_chat_id}"] = current_mc
                logger.debug(f"Queued peak_mc update for CA {ca} in VIP to {current_mc}")

        if public_data:
            public_initial_mc = public_data["initial_mc"]
            public_growth_ratio = current_mc / public_initial_mc if public_initial_mc != 0 else 0
            if current_mc > public_data.get("peak_mc", public_initial_mc):
                peak_updates[f"{ca}:{public_chat_id}"] = current_mc
                logger.debug(f"Queued peak_mc update for CA {ca} in Public to {current_mc}")

        # Check expiration and process notifications
        for chat_id, data in channel_data.items():
            token_time = datetime.fromtimestamp(data["timestamp"], pytz.timezone('America/New_York'))
            time_diff = (current_time - token_time).total_seconds() / 3600
            if time_diff > 6:  # 6 hours
                to_remove.append(f"{ca}:{chat_id}")
                logger.debug(f"CA {ca} in chat {chat_id} expired (time_diff: {time_diff:.2f}h)")
                continue

            if chat_id not in VIP_CHANNEL_IDS and chat_id not in PUBLIC_CHANNEL_IDS:
                logger.debug(f"Skipping CA {ca} in chat {chat_id} (not VIP or Public)")
                continue

            initial_mc = data["initial_mc"]
            token_name = data["token_name"]
            message_id = data["message_id"]
            timestamp = data["timestamp"]
            growth_ratio = current_mc / initial_mc if initial_mc != 0 else 0
            profit_percent = ((current_mc - initial_mc) / initial_mc) * 100 if initial_mc != 0 else 0

            # Check notification threshold
            key = f"{ca}:{chat_id}"
            last_ratio = last_growth_ratios.get(key, 1.0)
            next_threshold = int(last_ratio) + INCREMENT_THRESHOLD

            if growth_ratio >= GROWTH_THRESHOLD and growth_ratio >= next_threshold:
                last_growth_ratios[key] = growth_ratio
                time_since_added = calculate_time_since(timestamp)
                initial_mc_str = f"**{initial_mc / 1000:.1f}K**" if initial_mc < 1_000_000 else f"**{initial_mc / 1_000_000:.1f}M**"
                current_mc_str = f"**{current_mc / 1000:.1f}K**" if current_mc < 1_000_000 else f"**{current_mc / 1_000_000:.1f}M**"

                emoji = "🚀" if 2 <= growth_ratio < 5 else "🔥" if 5 <= growth_ratio < 10 else "🌙"
                growth_str = f"**{growth_ratio:.1f}x**"  # Bold growth ratio
                if chat_id in PUBLIC_CHANNEL_IDS and vip_data and vip_growth_ratio and public_growth_ratio and vip_growth_ratio > public_growth_ratio:
                    growth_str += f" (**{vip_growth_ratio:.1f}x** from VIP)"  # Bold VIP growth ratio

                symbol = token_name.split("|")[1].strip() if "|" in token_name else token_name
                growth_message = (
                    f"{emoji} {growth_str} | "
                    f"💹 From {initial_mc_str} ↗️ **{current_mc_str}** within **{time_since_added}** - {symbol}"
                )

                log_to_growthcheck_csv(
                    chat_id=chat_id, channel_id=chat_id, message_id=message_id,
                    token_name=token_name, ca=ca, original_mc=initial_mc,
                    current_mc=current_mc, growth_ratio=growth_ratio,
                    profit_percent=profit_percent, time_since_added=time_since_added,
                    is_vip_channel=(chat_id in VIP_CHANNEL_IDS)
                )
                log_to_csv(
                    ca=ca, token_name=token_name, bs_ratio=None, bs_ratio_pass=None,
                    check_low_pass=None, dev_sold=None, dev_sold_left_value=None,
                    dev_sold_pass=None, top_10=None, top_10_pass=None, snipers=None,
                    snipers_pass=None, bundles=None, bundles_pass=None, insiders=None,
                    insiders_pass=None, kols=None, kols_pass=None, bonding_curve=None,
                    bc_pass=None, overall_pass=None, original_mc=initial_mc,
                    current_mc=current_mc, growth_ratio=growth_ratio,
                    is_vip_channel=(chat_id in VIP_CHANNEL_IDS)
                )

                if growth_notifications_enabled:
                    try:
                        await bot.send_message(
                            chat_id=chat_id, text=growth_message,
                            parse_mode="Markdown", reply_to_message_id=message_id
                        )
                        logger.debug(f"Sent growth notification for CA {ca} in chat {chat_id}: {growth_message}")
                        logger.info(f"Sent growth notification for CA {ca} in chat {chat_id}: {growth_message}")
                    except Exception as e:
                        logger.debug(f"Failed to send growth notification for CA {ca} in chat {chat_id}: {e}")
                        logger.error(f"Failed to send growth notification for CA {ca} in chat {chat_id}: {e}")

            # New sub-chunk: 3x notification to dedicated channel
            time_diff_seconds = (current_time - token_time).total_seconds()
            if growth_ratio >= 2.3 and time_diff_seconds <= 150 and ca not in notified_cas:
                group_chat_id = -1002280798125
                current_mc_str = f"{current_mc / 1000:.1f}K" if current_mc < 1_000_000 else f"{current_mc / 1_000_000:.1f}M"
                growth_ratio_str = f"{growth_ratio:.1f}x"
                time_since = calculate_time_since(timestamp)
                notify_message = (
                    f"🚀 **{token_name}** hit **{growth_ratio_str}** in **{time_since}**!\n"
                    f"🔗 CA: `{ca}`\n"
                    f"💰 Current MC: **{current_mc_str}** - {symbol}"
                )
                try:
                    await bot.send_message(
                        chat_id=group_chat_id,
                        text=notify_message,
                        parse_mode="Markdown"
                    )
                    logger.debug(f"Notified group {group_chat_id} for CA {ca}: {growth_ratio:.1f}x in {time_since}")
                    logger.info(f"Notified group {group_chat_id} for CA {ca}: {growth_ratio:.1f}x in {time_since}")
                    notified_cas.add(ca)  # Mark CA as notified for Telegram
                except Exception as e:
                    logger.debug(f"Failed to notify group {group_chat_id} for CA {ca}: {e}")
                    logger.error(f"Failed to notify group {group_chat_id} for CA {ca}: {e}")

            # Twitter notification for first channel (VIP or Public) to reach 3x+ growth
            if (chat_id in VIP_CHANNEL_IDS or chat_id in PUBLIC_CHANNEL_IDS) and growth_ratio >= 3.0 and ca not in notified_cas_twitter:
                import tweepy
                client = tweepy.Client(
                    bearer_token=os.getenv("X_BEARER_TOKEN"),
                    consumer_key=os.getenv("X_CONSUMER_KEY"),
                    consumer_secret=os.getenv("X_CONSUMER_SECRET"),
                    access_token=os.getenv("X_ACCESS_TOKEN"),
                    access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET")
                )
                initial_mc_str_plain = f"{initial_mc / 1000:.1f}K" if initial_mc < 1_000_000 else f"{initial_mc / 1_000_000:.1f}M"
                current_mc_str_plain = f"{current_mc / 1000:.1f}K" if current_mc < 1_000_000 else f"{current_mc / 1_000_000:.1f}M"
                roi_percent = profit_percent if profit_percent > 0 else 0
                tweet_variations = [
                    f"🌟 {token_name} just hit 3x+ growth!\nInitial MC: ${initial_mc_str_plain}\nCurrent MC: ${current_mc_str_plain}\nROI: {roi_percent:.0f}%\nCA: {ca} Join us: https://t.me/HumbleApes\n#solana #pump #bonk",
                    f"🎉 {token_name} soared 3x+!\nInitial MC: ${initial_mc_str_plain}\nCurrent MC: ${current_mc_str_plain}\nROI: {roi_percent:.0f}%\nCA: {ca} Join us: https://t.me/HumbleApes\n#solana #pump #bonk",
                    f"🔥 {token_name} reached 3x+ growth!\nInitial MC: ${initial_mc_str_plain}\nCurrent MC: ${current_mc_str_plain}\nROI: {roi_percent:.0f}%\nCA: {ca} Join us: https://t.me/HumbleApes\n#solana #pump #bonk",
                    f"🚀 {token_name} climbed 3x+!\nInitial MC: ${initial_mc_str_plain}\nCurrent MC: ${current_mc_str_plain}\nROI: {roi_percent:.0f}%\nCA: {ca} Join us: https://t.me/HumbleApes\n#solana #pump #bonk",
                    f"💎 {token_name} hit 3x+ growth!\nInitial MC: ${initial_mc_str_plain}\nCurrent MC: ${current_mc_str_plain}\nROI: {roi_percent:.0f}%\nCA: {ca} Join us: https://t.me/HumbleApes\n#solana #pump #bonk"
                ]
                import random
                tweet_text = random.choice(tweet_variations)
                try:
                    response = client.create_tweet(text=tweet_text)
                    if response and response.data and response.data.get("id"):
                        logger.debug(f"Posted Twitter update for CA {ca} at {growth_ratio:.1f}x growth: {tweet_text}")
                        logger.info(f"Posted Twitter update for CA {ca} at {growth_ratio:.1f}x growth: {tweet_text}")
                        notified_cas_twitter.add(ca)  # Mark CA as notified for Twitter to prevent duplicates
                    else:
                        logger.debug(f"Failed to verify Twitter update for CA {ca}: {response}")
                        logger.error(f"Failed to verify Twitter update for CA {ca}: {response}")
                except Exception as e:
                    logger.debug(f"Failed to post Twitter update for CA {ca} at {growth_ratio:.1f}x: {e}")
                    logger.error(f"Failed to post Twitter update for CA {ca} at {growth_ratio:.1f}x: {e}")

    # Apply updates after iteration
    for key, peak_mc in peak_updates.items():
        monitored_tokens[key]["peak_mc"] = peak_mc
    for key in to_remove:
        monitored_tokens.pop(key, None)
        last_growth_ratios.pop(key, None)
    if peak_updates or to_remove:
        save_monitored_tokens()
        logger.debug(f"Updated {len(peak_updates)} peak_mcs and removed {len(to_remove)} expired tokens")
        logger.info(f"Updated {len(peak_updates)} peak_mcs and removed {len(to_remove)} expired tokens")
        
router = Router()

async def daily_summary_report() -> None:
    logger.info("Generating daily summary report")
    current_time = datetime.now(pytz.timezone('America/New_York'))
    today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_ts = today_start.timestamp()
    logger.debug(f"Today start timestamp: {today_start_ts}")
    
    # Read vip_growthcheck_log.csv using the correct path
    GROWTHCHECK_LOG_CSV_FILE = VIP_GROWTH_CSV_FILE  # Use the defined path /app/data/vip_growthcheck_log.csv
    qualifying_tokens = []
    if os.path.exists(GROWTHCHECK_LOG_CSV_FILE):
        logger.debug(f"Reading growth check tokens from {GROWTHCHECK_LOG_CSV_FILE}")
        with open(GROWTHCHECK_LOG_CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            logger.debug(f"Found {len(rows)} total tokens in {GROWTHCHECK_LOG_CSV_FILE}")
            logger.debug(f"CSV columns: {reader.fieldnames}")
            for row in rows:
                # Convert Timestamp string to float (Unix timestamp)
                timestamp_str = row["Timestamp"]
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.timezone('America/New_York')).timestamp()
                logger.debug(f"Processing token with CA={row['CA']}, Timestamp={timestamp}")
                if timestamp < today_start_ts:
                    logger.debug(f"Skipping token with timestamp {timestamp} (before today)")
                    continue  # Skip tokens not from today
                chat_id = int(row["ChatID"])
                logger.debug(f"Checking chat_id {chat_id} against VIP_CHANNEL_IDS {VIP_CHANNEL_IDS}")
                if chat_id not in VIP_CHANNEL_IDS:
                    logger.debug(f"Skipping token with chat_id {chat_id} (not in VIP channels)")
                    continue  # Only include tokens from VIP channels
                original_mc = float(row["OriginalMC"])
                current_mc = float(row["CurrentMC"])
                growth_ratio = float(row.get("GrowthRatio", 0))  # Use CSV GrowthRatio directly
                logger.debug(f"Calculated growth ratio for CA {row['CA']}: {growth_ratio:.1f}x")
                if growth_ratio >= 2.1:
                    # Extract only the symbol (e.g., $SCHOOL) from TokenName
                    token_name = row.get("TokenName", "$Unknown")
                    logger.debug(f"Raw TokenName: {token_name}")  # Log raw value for debugging
                    if token_name == "$Unknown":
                        logger.warning(f"No 'TokenName' column found for CA={row['CA']}.")
                    # Extract $SYMBOL by splitting on | and taking the part after it
                    if '|' in token_name:
                        symbol = token_name.split('|')[1].strip().split(' ')[0]  # Take the part after | and first word
                        symbol = f"${symbol}" if not symbol.startswith('$') else symbol  # Ensure $ prefix
                    else:
                        symbol = "$Unknown"  # Fallback if format doesn't match
                    logger.debug(f"Extracted symbol: {symbol}")
                    qualifying_tokens.append({
                        "symbol": symbol,
                        "ca": row["CA"],
                        "growth_ratio": growth_ratio,
                        "current_mc": current_mc,
                        "chat_id": chat_id
                    })
    else:
        logger.warning(f"Growth check log file {GROWTHCHECK_LOG_CSV_FILE} does not exist")
        return

    # Sort tokens by growth ratio (descending)
    qualifying_tokens.sort(key=lambda x: x["growth_ratio"], reverse=True)

    # Generate report
    if not qualifying_tokens:
        logger.info("No VIP tokens with growth ratio >= 2.1x for today")
        return

    date_str = current_time.strftime("%d/%m/%Y")
    report = (
        f"📈 **Top Performing VIP Tokens** 📈\n"
        f"📅 {date_str}\n\n"
    )

    # Add each token to the report
    for idx, token in enumerate(qualifying_tokens, 1):
        symbol = token["symbol"]
        ca = token["ca"]
        growth_ratio = token["growth_ratio"]
        pump_fun_url = f"https://pump.fun/coin/{ca}"
        emoji = "🏆" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "🏅"
        # Use ├ for all items except the last, which uses └
        prefix = "├" if idx < len(qualifying_tokens) else "└"
        # Align symbol and growth ratio with fixed-width spacing (10 characters for symbol field)
        symbol_field = symbol.ljust(10)
        report += (
            f"{prefix}{emoji} 👀 | [{chr(0x1F517)}]({pump_fun_url}) | {symbol_field} | {growth_ratio:.1f}x\n"
        )

    # Add footer
    report += "\nJoin our VIP channel for more gains! 💰\n"

    # Create inline keyboard with Join VIP button
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌟🚀 Join VIP 🚀🌟", url="https://t.me/HumbleMoonshotsPay_bot?start=start")]
    ])

    # Post to public channel
    public_chat_id = list(PUBLIC_CHANNEL_IDS)[0]
    try:
        message = await bot.send_message(
            chat_id=public_chat_id,
            text=report,
            parse_mode="Markdown",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )
        logger.info(f"Posted daily VIP summary report to public channel {public_chat_id}, message_id={message.message_id}")

        # Pin the message
        await bot.pin_chat_message(
            chat_id=public_chat_id,
            message_id=message.message_id,
            disable_notification=True
        )
        logger.info(f"Pinned daily VIP summary report message {message.message_id} in public channel {public_chat_id}")
    except Exception as e:
        logger.error(f"Failed to post or pin daily VIP summary report: {e}")

# Add the /dailysummary command handler
@router.message(Command("dailysummary"))
async def cmd_dailysummary(message: types.Message):
    await daily_summary_report()
    await message.reply("Daily summary report has been generated and posted to the public channel.")
    
# Chunk 4 ends
"""
# Chunk 5 starts
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

    token_data = await get_gmgn_token_data(token_ca)
    if "error" in token_data:
        await message.reply(f"Error: {token_data['error']}")
    else:
        # Parse price by removing '$' and converting to float
        price = float(token_data['price'].replace('$', ''))
        # Parse liquidity and format it
        liquidity = parse_market_cap(token_data['liquidity'])
        liquidity_str = format_market_cap(liquidity)
        response = (
            f"Token Data for CA: {token_data['contract']}\n"
            f"📈 Market Cap: ${format_market_cap(token_data['market_cap'])}\n"
            f"💧 Liquidity: ${liquidity_str}\n"
            f"💰 Price: ${price:.6f}"
        )
        await message.reply(response)
"""
# Chunk 5 ends

# Chunk 6 starts
# Chunk 6a starts
async def log_update(handler, event: types.Update, data: dict):
    logger.info(f"Raw update received: {event}")
    return await handler(event, data)

dp.update.middleware(log_update)

@dp.message(Command(commands=["test"]))
async def test_command(message: types.Message):
    try:
        username = message.from_user.username
        logger.info(f"Test command received from @{username}")
        await message.answer("Test command works!")
    except Exception as e:
        logger.error(f"Error in test_command: {e}")
        await message.answer(f"Error: {e}")

@dp.message(Command(commands=["ca"]))
async def cmd_ca(message: types.Message):
    try:
        username = message.from_user.username
        logger.info(f"Received /ca command from @{username}")
        if not is_authorized(username):
            await message.answer("⚠️ You are not authorized to use this command.")
            logger.info(f"Unauthorized /ca attempt by @{username}")
            return
        
        text = message.text
        parts = text.split()
        if len(parts) != 2:
            await message.answer("Usage: /ca <token_ca>")
            return
        
        token_ca = parts[1].strip()
        logger.info(f"Processing token CA: {token_ca}")

        token_data = await get_gmgn_token_data(token_ca)
        if "error" in token_data:
            await message.reply(f"Error: {token_data['error']}")
            return

        price = token_data.get('price', 'N/A')
        market_cap_str = token_data.get('market_cap_str', 'N/A')
        liquidity = float(token_data.get('liquidity', '0'))
        token_name = token_data.get('name', 'Unknown')
        circulating_supply = token_data.get('circulating_supply', 0)

        if price != "N/A":
            price_float = float(price)
            price_display = f"{price_float:.1e}" if price_float < 0.001 else f"{price_float:.6f}"
        else:
            price_display = "N/A"

        supply_str = f"{circulating_supply:,.0f}" if circulating_supply != 0 else "N/A"
        response = (
            f"**Token Data**\n\n"
            f"🔖 Token Name: {token_name}\n"
            f"📍 CA: `{token_ca}`\n"
            f"📈 Market Cap: ${market_cap_str}\n"
            f"💧 Liquidity: ${liquidity:.2f}\n"
            f"💰 Price: ${price_display}\n"
            f"📦 Circulating Supply: {supply_str}"
        )

        await message.reply(response, parse_mode="Markdown")
        logger.info(f"Sent token data for CA {token_ca} to @{username}")
    except Exception as e:
        logger.error(f"Error in cmd_ca: {e}")
        await message.answer(f"Error processing /ca: {str(e)}")

@dp.message(Command(commands=["setfilter"]))
async def set_filter(message: types.Message):
    try:
        username = message.from_user.username
        logger.info(f"Received /setfilter command from user: @{username}")
        if not is_authorized(username):
            await message.answer("⚠️ You are not authorized to use this command.")
            logger.info(f"Unauthorized /setfilter attempt by @{username}")
            return
        global filter_enabled
        text = message.text.lower().replace('/setfilter', '').strip()
        if text == "yes":
            filter_enabled = True
            await message.answer("Filter enabled: Yes ✅")
            logger.info("Filter enabled")
        elif text == "no":
            filter_enabled = False
            await message.answer("Filter enabled: No 🚫")
            logger.info("Filter disabled")
        else:
            await message.answer("Please specify Yes or No after /setfilter (e.g., /setfilter Yes) 🤔")
            logger.info("Invalid /setfilter input")
    except Exception as e:
        logger.error(f"Error in set_filter: {e}")
        await message.answer(f"Error processing /setfilter: {e}")

# ... (other handlers like setcheckhigh, setchecklow, etc., unchanged up to downloadcsv)

# Handler for /checkhigh command to enable/disable CheckHigh filter
@dp.message(Command(commands=["setcheckhigh"]))
async def toggle_checkhigh(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setcheckhigh command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setcheckhigh attempt by @{username}")
        return
    global CheckHighEnabled
    text = message.text.lower().replace('/setcheckhigh', '').strip()
    logger.info(f"Received /setcheckhigh command with text: {text}")
    if text == "yes":
        CheckHighEnabled = True
        await message.answer("CheckHigh filter set to: Yes ✅")
        logger.info("CheckHigh filter enabled")
    elif text == "no":
        CheckHighEnabled = False
        await message.answer("CheckHigh filter set to: No 🚫")
        logger.info("CheckHigh filter disabled")
    else:
        await message.answer("Please specify Yes or No after /setcheckhigh (e.g., /setcheckhigh Yes) 🤔")
        logger.info("Invalid /setcheckhigh input")

# Handler for /checklow command to enable/disable CheckLow filter
@dp.message(Command(commands=["setchecklow"]))
async def toggle_checklow(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setchecklow command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setchecklow attempt by @{username}")
        return
    global CheckLowEnabled
    text = message.text.lower().replace('/setchecklow', '').strip()
    logger.info(f"Received /setchecklow command with text: {text}")
    if text == "yes":
        CheckLowEnabled = True
        await message.answer("CheckLow filter set to: Yes ✅")
        logger.info("CheckLow filter enabled")
    elif text == "no":
        CheckLowEnabled = False
        await message.answer("CheckLow filter set to: No 🚫")
        logger.info("CheckLow filter disabled")
    else:
        await message.answer("Please specify Yes or No after /setchecklow (e.g., /setchecklow Yes) 🤔")
        logger.info("Invalid /setchecklow input")

# Handler for /setpassvalue command to set PassValue (for CheckHigh)
@dp.message(Command(commands=["setpassvalue"]))
async def setup_val(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setpassvalue command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setpassvalue attempt by @{username}")
        return
    global PassValue
    text = message.text.lower().replace('/setpassvalue', '').strip()
    logger.info(f"Received /setpassvalue command with text: {text}")
    try:
        value = float(text)
        PassValue = value
        await message.answer(f"PassValue set to: {PassValue} ✅")
        logger.info(f"PassValue updated to: {PassValue}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /setpassvalue 1.2) 🚫")
        logger.info("Invalid /setpassvalue input: not a number")

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

# Handler for /setdevsoldthreshold command (Yes/No)
@dp.message(Command(commands=["setdevsoldthreshold"]))
async def set_devsold(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setdevsoldthreshold command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setdevsoldthreshold attempt by @{username}")
        return
    global DevSoldThreshold
    text = message.text.lower().replace('/setdevsoldthreshold', '').strip()
    if text in ["yes", "no"]:
        DevSoldThreshold = text.capitalize()
        await message.answer(f"DevSoldThreshold set to: {DevSoldThreshold} ✅")
        logger.info(f"DevSoldThreshold updated to: {DevSoldThreshold}")
    else:
        await message.answer("Please specify Yes or No (e.g., /setdevsoldthreshold Yes) 🚫")
        logger.info("Invalid /setdevsoldthreshold input")

# Handler for /setdevsoldleft command (numerical percentage)
@dp.message(Command(commands=["setdevsoldleft"]))
async def set_devsoldleft(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setdevsoldleft command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setdevsoldleft attempt by @{username}")
        return
    global DevSoldLeft
    text = message.text.lower().replace('/setdevsoldleft', '').strip()
    try:
        value = float(text)
        if value < 0 or value > 100:
            await message.answer("Please provide a percentage between 0 and 100 (e.g., /setdevsoldleft 10) 🚫")
            logger.info("Invalid /setdevsoldleft input: out of range")
            return
        DevSoldLeft = value
        await message.answer(f"DevSoldLeft threshold set to: {DevSoldLeft}% ✅")
        logger.info(f"DevSoldLeft updated to: {DevSoldLeft}")
    except ValueError:
        await message.answer("Please provide a valid numerical percentage (e.g., /setdevsoldleft 10) 🚫")
        logger.info("Invalid /setdevsoldleft input: not a number")

# Handler for /setdevsoldfilter command
@dp.message(Command(commands=["setdevsoldfilter"]))
async def toggle_devsold_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setdevsoldfilter command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setdevsoldfilter attempt by @{username}")
        return
    global DevSoldFilterEnabled
    text = message.text.lower().replace('/setdevsoldfilter', '').strip()
    if text == "yes":
        DevSoldFilterEnabled = True
        await message.answer("DevSold filter set to: Yes ✅")
        logger.info("DevSold filter enabled")
    elif text == "no":
        DevSoldFilterEnabled = False
        await message.answer("DevSold filter set to: No 🚫")
        logger.info("DevSold filter disabled")
    else:
        await message.answer("Please specify Yes or No after /setdevsoldfilter (e.g., /setdevsoldfilter Yes) 🤔")
        logger.info("Invalid /setdevsoldfilter input")

# Handler for /settop10threshold command
@dp.message(Command(commands=["settop10threshold"]))
async def set_top10(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /settop10threshold command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /settop10threshold attempt by @{username}")
        return
    global Top10Threshold
    text = message.text.lower().replace('/settop10threshold', '').strip()
    try:
        value = float(text)
        Top10Threshold = value
        await message.answer(f"Top10Threshold set to: {Top10Threshold} ✅")
        logger.info(f"Top10Threshold updated to: {Top10Threshold}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /settop10threshold 20) 🚫")
        logger.info("Invalid /settop10threshold input: not a number")

# Handler for /settop10filter command
@dp.message(Command(commands=["settop10filter"]))
async def toggle_top10_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /settop10filter command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /settop10filter attempt by @{username}")
        return
    global Top10FilterEnabled
    text = message.text.lower().replace('/settop10filter', '').strip()
    if text == "yes":
        Top10FilterEnabled = True
        await message.answer("Top10 filter set to: Yes ✅")
        logger.info("Top10 filter enabled")
    elif text == "no":
        Top10FilterEnabled = False
        await message.answer("Top10 filter set to: No 🚫")
        logger.info("Top10 filter disabled")
    else:
        await message.answer("Please specify Yes or No after /settop10filter (e.g., /settop10filter Yes) 🤔")
        logger.info("Invalid /settop10filter input")

# Handler for /setsnipersthreshold command
@dp.message(Command(commands=["setsnipersthreshold"]))
async def set_snipers(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setsnipersthreshold command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setsnipersthreshold attempt by @{username}")
        return
    global SnipersThreshold
    text = message.text.lower().replace('/setsnipersthreshold', '').strip()
    try:
        value = float(text)
        SnipersThreshold = value
        await message.answer(f"SnipersThreshold set to: {SnipersThreshold} ✅")
        logger.info(f"SnipersThreshold updated to: {SnipersThreshold}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /setsnipersthreshold 3) 🚫")
        logger.info("Invalid /setsnipersthreshold input: not a number")

# Handler for /setsnipersfilter command
@dp.message(Command(commands=["setsnipersfilter"]))
async def toggle_snipers_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setsnipersfilter command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setsnipersfilter attempt by @{username}")
        return
    global SniphersFilterEnabled
    text = message.text.lower().replace('/setsnipersfilter', '').strip()
    if text == "yes":
        SniphersFilterEnabled = True
        await message.answer("Snipers filter set to: Yes ✅")
        logger.info("Snipers filter enabled")
    elif text == "no":
        SniphersFilterEnabled = False
        await message.answer("Snipers filter set to: No 🚫")
        logger.info("Snipers filter disabled")
    else:
        await message.answer("Please specify Yes or No after /setsnipersfilter (e.g., /setsnipersfilter Yes) 🤔")
        logger.info("Invalid /setsnipersfilter input")

# Handler for /setbundlesthreshold command
@dp.message(Command(commands=["setbundlesthreshold"]))
async def set_bundles(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setbundlesthreshold command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setbundlesthreshold attempt by @{username}")
        return
    global BundlesThreshold
    text = message.text.lower().replace('/setbundlesthreshold', '').strip()
    try:
        value = float(text)
        BundlesThreshold = value
        await message.answer(f"BundlesThreshold set to: {BundlesThreshold} ✅")
        logger.info(f"BundlesThreshold updated to: {BundlesThreshold}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /setbundlesthreshold 1) 🚫")
        logger.info("Invalid /setbundlesthreshold input: not a number")

# Handler for /setbundlesfilter command
@dp.message(Command(commands=["setbundlesfilter"]))
async def toggle_bundles_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setbundlesfilter command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setbundlesfilter attempt by @{username}")
        return
    global BundlesFilterEnabled
    text = message.text.lower().replace('/setbundlesfilter', '').strip()
    if text == "yes":
        BundlesFilterEnabled = True
        await message.answer("Bundles filter set to: Yes ✅")
        logger.info("Bundles filter enabled")
    elif text == "no":
        BundlesFilterEnabled = False
        await message.answer("Bundles filter set to: No 🚫")
        logger.info("Bundles filter disabled")
    else:
        await message.answer("Please specify Yes or No after /setbundlesfilter (e.g., /setbundlesfilter Yes) 🤔")
        logger.info("Invalid /setbundlesfilter input")

# Handler for /setinsidersthreshold command
@dp.message(Command(commands=["setinsidersthreshold"]))
async def set_insiders(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setinsidersthreshold command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setinsidersthreshold attempt by @{username}")
        return
    global InsidersThreshold
    text = message.text.lower().replace('/setinsidersthreshold', '').strip()
    try:
        value = float(text)
        InsidersThreshold = value
        await message.answer(f"InsidersThreshold set to: {InsidersThreshold} ✅")
        logger.info(f"InsidersThreshold updated to: {InsidersThreshold}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /setinsidersthreshold 10) 🚫")
        logger.info("Invalid /setinsidersthreshold input: not a number")

# Handler for /setinsidersfilter command
@dp.message(Command(commands=["setinsidersfilter"]))
async def toggle_insiders_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setinsidersfilter command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setinsidersfilter attempt by @{username}")
        return
    global InsidersFilterEnabled
    text = message.text.lower().replace('/setinsidersfilter', '').strip()
    if text == "yes":
        InsidersFilterEnabled = True
        await message.answer("Insiders filter set to: Yes ✅")
        logger.info("Insiders filter enabled")
    elif text == "no":
        InsidersFilterEnabled = False
        await message.answer("Insiders filter set to: No 🚫")
        logger.info("Insiders filter disabled")
    else:
        await message.answer("Please specify Yes or No after /setinsidersfilter (e.g., /setinsidersfilter Yes) 🤔")
        logger.info("Invalid /setinsidersfilter input")

# Handler for /setkolsthreshold command
@dp.message(Command(commands=["setkolsthreshold"]))
async def set_kols(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setkolsthreshold command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setkolsthreshold attempt by @{username}")
        return
    global KOLsThreshold
    text = message.text.lower().replace('/setkolsthreshold', '').strip()
    try:
        value = float(text)
        KOLsThreshold = value
        await message.answer(f"KOLsThreshold set to: {KOLsThreshold} ✅")
        logger.info(f"KOLsThreshold updated to: {KOLsThreshold}")
    except ValueError:
        await message.answer("Please provide a valid numerical value (e.g., /setkolsthreshold 1) 🚫")
        logger.info("Invalid /setkolsthreshold input: not a number")

# Handler for /setkolsfilter command
@dp.message(Command(commands=["setkolsfilter"]))
async def toggle_kols_filter(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setkolsfilter command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setkolsfilter attempt by @{username}")
        return
    global KOLsFilterEnabled
    text = message.text.lower().replace('/setkolsfilter', '').strip()
    if text == "yes":
        KOLsFilterEnabled = True
        await message.answer("KOLs filter set to: Yes ✅")
        logger.info("KOLs filter enabled")
    elif text == "no":
        KOLsFilterEnabled = False
        await message.answer("KOLs filter set to: No 🚫")
        logger.info("KOLs filter disabled")
    else:
        await message.answer("Please specify Yes or No after /setkolsfilter (e.g., /setkolsfilter Yes) 🤔")
        logger.info("Invalid /setkolsfilter input")

# Handler for /adduser command
@dp.message(Command(commands=["adduser"]))
async def add_user(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /adduser command from user: @{username}")
    if username != "BeingHumbleGuy":
        await message.answer("⚠️ Only @BeingHumbleGuy can use this command.")
        logger.info(f"Unauthorized /adduser attempt by @{username}")
        return
    text = message.text.replace('/adduser', '').strip()
    if not text.startswith('@'):
        await message.answer("Please provide a username starting with @ (e.g., /adduser @NewUser) 🤔")
        logger.info("Invalid /adduser input: no @username provided")
        return
    new_user = text
    if new_user in authorized_users:
        await message.answer(f"{new_user} is already authorized ✅")
        logger.info(f"User {new_user} already in authorized_users")
    else:
        authorized_users.append(new_user)
        await message.answer(f"Added {new_user} to authorized users ✅")
        logger.info(f"Added {new_user} to authorized_users")

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
    download_url = f"{base_url}/download/public_ca_filter_log.csv?token={DOWNLOAD_TOKEN}"
    if not os.path.exists("/app/data/public_ca_filter_log.csv"):
        await message.answer("⚠️ No CSV file exists yet. Process some messages to generate data.")
        logger.info("CSV file not found for /downloadcsv")
        return
    await message.answer(
        f"Click the link to download or view the CSV file:\n{download_url}\n"
        "Note: This link is private and should not be shared."
    )
    logger.info(f"Provided CSV download link to @{username}: {download_url}")

@dp.message(Command(commands=["downloadgrowthcsv"]))
async def download_growth_csv_command(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /downloadgrowthcsv command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /downloadgrowthcsv attempt by @{username}")
        return
    base_url = os.getenv("RAILWAY_PUBLIC_DOMAIN", "http://localhost:5000")
    if base_url == "http://localhost:5000" and "RAILWAY_PUBLIC_DOMAIN" not in os.environ:
        logger.warning("RAILWAY_PUBLIC_DOMAIN not set, using localhost:5000 (this won't work on Railway)")
    
    public_url = f"{base_url}/download/public_growthcheck_log.csv?token={DOWNLOAD_TOKEN}"
    vip_url = f"{base_url}/download/vip_growthcheck_log.csv?token={DOWNLOAD_TOKEN}"
    
    response = "📊 **Growth Check CSV Downloads**\n\n"
    if os.path.exists(PUBLIC_GROWTH_CSV_FILE):
        response += f"Public Channel: [Download]({public_url})\n"
    else:
        response += "Public Channel: No data yet\n"
    
    if os.path.exists(VIP_GROWTH_CSV_FILE):
        response += f"VIP Channel: [Download]({vip_url})\n"
    else:
        response += "VIP Channel: No data yet\n"
    
    response += "\nNote: These links are private and should not be shared."
    
    await message.answer(response, parse_mode="Markdown")
    logger.info(f"Provided growth check CSV download links to @{username}")
    
    
    # Add new command in Chunk 6a (after /downloadgrowthcsv, around line ~1300)
@dp.message(Command(commands=["downloadmonitoredtokens"]))
async def download_monitored_tokens(message: types.Message) -> None:
    username = message.from_user.username
    logger.info(f"Received /downloadmonitoredtokens command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /downloadmonitoredtokens attempt by @{username}")
        return
    
    base_url = os.getenv("RAILWAY_PUBLIC_DOMAIN", "http://localhost:5000")
    if base_url == "http://localhost:5000" and "RAILWAY_PUBLIC_DOMAIN" not in os.environ:
        logger.warning("RAILWAY_PUBLIC_DOMAIN not set, using localhost:5000 (this won't work on Railway)")
    download_url = f"{base_url}/download/monitored_tokens.csv?token={DOWNLOAD_TOKEN}"
    
    file_path = MONITORED_TOKENS_CSV_FILE
    file_exists = os.path.exists(file_path)
    file_size = os.path.getsize(file_path) if file_exists else 0
    logger.debug(f"Checking file: {file_path}, exists={file_exists}, size={file_size} bytes")
    
    if not file_exists:
        response = (
            "⚠️ No `monitored_tokens.csv` file exists yet.\n"
            "This file is generated when 'Fasol' messages are processed in VIP or Public channels.\n"
            "Please post a 'Fasol' message (e.g., 'Fasol CA123 MC: $10K') in a monitored channel."
        )
    elif file_size <= len(','.join(["CA:ChatID", "TokenName", "InitialMC", "PeakMC", "Timestamp", "MessageID", "ChatID"]) + '\n'):
        response = (
            "⚠️ `monitored_tokens.csv` exists but is empty (only headers).\n"
            "No tokens are being monitored yet. Post a 'Fasol' message in VIP/Public channels to populate it."
        )
    else:
        response = (
            f"Click the link to download or view the monitored tokens CSV file:\n{download_url}\n"
            "Note: This link is private and should not be shared."
        )
    
    await message.reply(response, parse_mode="Markdown")
    logger.info(f"Responded to @{username} for /downloadmonitoredtokens: {response[:100]}...")

# Chunk 6a ends

# Chunk 6b starts
@dp.message(Command(commands=["growthnotify"]))
async def toggle_growth_notify(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /growthnotify command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /growthnotify attempt by @{username}")
        return
    global growth_notifications_enabled
    text = message.text.lower().replace('/growthnotify', '').strip()
    if text == "yes":
        growth_notifications_enabled = True
        await message.answer("Growth notifications set to: Yes ✅")
        logger.info("Growth notifications enabled")
    elif text == "no":
        growth_notifications_enabled = False
        await message.answer("Growth notifications set to: No 🚫")
        logger.info("Growth notifications disabled")
    else:
        await message.answer("Please specify Yes or No after /growthnotify (e.g., /growthnotify Yes) 🤔")
        logger.info("Invalid /growthnotify input")

# ... (other handlers like mastersetup, resetdefaults unchanged)

# Chunk 6b starts (continued)

# Handler for /setpnlreport command to enable/disable PNL report generation
@dp.message(Command(commands=["setpnlreport"]))
async def toggle_pnl_report(message: types.Message):
    username = message.from_user.username
    logger.info(f"[PNLREPORT] Received /setpnlreport command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ Only authorized users can use this command.")
        logger.info(f"[PNLREPORT] Unauthorized /setpnlreport attempt by @{username}")
        return
    global pnl_report_enabled
    text = message.text.lower().replace('/setpnlreport', '').strip()
    if text == "yes":
        pnl_report_enabled = True
        await message.answer("PNL report generation set to: Yes ✅")
        logger.info("[PNLREPORT] PNL report generation enabled")
    elif text == "no":
        pnl_report_enabled = False
        await message.answer("PNL report generation set to: No ⛔")
        logger.info("[PNLREPORT] PNL report generation disabled")
    else:
        await message.answer("Please specify Yes or No after /setpnlreport (e.g., /setpnlreport Yes) 🤔")
        logger.info("[PNLREPORT] Invalid /setpnlreport input")

# Function to generate PNL report for top 10 tokens with 10-minute intervals
async def generate_pnl_report(context="scheduled"):
    if not pnl_report_enabled:
        logger.info(f"PNL report generation ({context}) is disabled, skipping execution")
        return

    logger.info(f"Generating PNL report ({context}) for top 10 tokens with 10-minute intervals")
    current_time = datetime.now(pytz.timezone('America/New_York'))
    today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_ts = today_start.timestamp()
    logger.debug(f"Today start timestamp: {today_start_ts}")

    qualifying_tokens = []
    GROWTHCHECK_LOG_CSV_FILE = VIP_GROWTH_CSV_FILE  # /app/data/vip_growthcheck_log.csv
    if os.path.exists(GROWTHCHECK_LOG_CSV_FILE):
        logger.debug(f"Reading growth check tokens from {GROWTHCHECK_LOG_CSV_FILE}")
        with open(GROWTHCHECK_LOG_CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            logger.debug(f"Found {len(rows)} total tokens in {GROWTHCHECK_LOG_CSV_FILE}")
            for row in rows:
                timestamp_str = row["Timestamp"]
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.timezone('America/New_York')).timestamp()
                if timestamp < today_start_ts:
                    logger.debug(f"Skipping token with timestamp {timestamp} (before today)")
                    continue
                if int(row["ChatID"]) not in VIP_CHANNEL_IDS:
                    logger.debug(f"Skipping token with chat_id {row['ChatID']} (not in VIP channels)")
                    continue
                growth_ratio = float(row.get("GrowthRatio", 0))
                qualifying_tokens.append({
                    "ca": row["CA"],
                    "growth_ratio": growth_ratio,
                    "token_name": row.get("TokenName", "$Unknown")
                })
    else:
        logger.warning(f"Growth check log file {GROWTHCHECK_LOG_CSV_FILE} does not exist")
        return

    # Sort by growth ratio and take top 10
    qualifying_tokens.sort(key=lambda x: x["growth_ratio"], reverse=True)
    top_10_tokens = qualifying_tokens[:10]
    logger.info(f"Processing {len(top_10_tokens)} qualifying tokens for PNL report ({context})")

    if not top_10_tokens:
        logger.info(f"No VIP tokens found for PNL report ({context})")
        return

    vip_chat_id = list(VIP_CHANNEL_IDS)[0]  # -1002365061913
    logger.debug(f"Using VIP channel ID: {vip_chat_id}")
    public_chat_id = list(PUBLIC_CHANNEL_IDS)[0]  # -1002272066154

    # Process each CA with 10-minute interval
    for i, token in enumerate(top_10_tokens):
        ca = token["ca"]
        logger.info(f"Processing PNL for CA {ca} (Token: {token['token_name']}) at index {i} ({context})")
        max_retries = 3
        success = False
        for attempt in range(max_retries):
            try:
                # Send /pnl <ca> command to VIP channel
                pnl_message = await bot.send_message(
                    chat_id=vip_chat_id,
                    text=f"/pnl {ca}",
                    parse_mode=None
                )
                logger.info(f"Sent /pnl {ca} to VIP channel {vip_chat_id}, message_id={pnl_message.message_id} ({context})")

                # Wait for PhanesGreenBot to post the first comment with the image (initial wait: 10 seconds)
                await asyncio.sleep(10)
                logger.debug(f"Attempting to fetch comments for message_id {pnl_message.message_id} ({context})")
                # Retry fetching comments multiple times
                photo = None
                for retry in range(3):
                    try:
                        comments = await bot.get_forum_topic_messages(
                            chat_id=vip_chat_id,
                            message_thread_id=pnl_message.message_id,
                            limit=1
                        )
                        logger.debug(f"Fetched comments (attempt {retry + 1}): {comments.messages} ({context})")
                        if comments.messages and comments.messages[0].photo:
                            photo = comments.messages[0].photo[-1]  # Get the highest resolution
                            break
                        logger.debug(f"No comments found on attempt {retry + 1}, retrying in 5 seconds ({context})")
                        await asyncio.sleep(5)
                    except Exception as e:
                        logger.error(f"Error fetching comments on attempt {retry + 1} for CA {ca} ({context}): {e}")
                        if retry < 2:
                            await asyncio.sleep(5)
                            continue
                        raise

                # Fallback to get_updates if get_forum_topic_messages fails
                if not photo:
                    logger.debug(f"Falling back to get_updates for message_id {pnl_message.message_id} ({context})")
                    updates = await bot.get_updates(offset=pnl_message.message_id, limit=10, timeout=10)
                    logger.debug(f"Fetched updates: {updates} ({context})")
                    for update in updates:
                        if (update.message and update.message.reply_to_message and
                            update.message.reply_to_message.message_id == pnl_message.message_id and
                            hasattr(update.message, 'photo') and update.message.photo):
                            photo = update.message.photo[-1]
                            logger.debug(f"Found image in updates for CA {ca} ({context})")
                            break

                if photo:
                    # Send photo directly to public channel with "Join VIP" button
                    markup = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🌟🚀 Join VIP 🚀🌟", url="https://t.me/HumbleMoonshotsPay_bot?start=start")]
                    ])
                    await bot.send_photo(
                        chat_id=public_chat_id,
                        photo=photo.file_id,
                        caption=f"PNL for {token['token_name']} (CA: {ca})",
                        reply_markup=markup
                    )
                    logger.info(f"Sent PNL image for CA {ca} to public channel {public_chat_id} as channel post ({context})")
                    success = True
                else:
                    logger.warning(f"No image found in comments or updates for CA {ca} from PhanesGreenBot ({context})")

                break  # Exit retry loop on success or after max retries
            except Exception as e:
                logger.error(f"Error processing PNL for CA {ca} on attempt {attempt + 1} ({context}): {e}")
                if "Conflict: terminated by other getUpdates request" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Conflict error, retrying after 5 seconds ({context})...")
                    await asyncio.sleep(5)
                    continue
                break

        # Enforce 10-minute interval after each token, even on error
        if i < len(top_10_tokens) - 1:
            wait_time = 600  # Fixed 10-minute interval
            logger.debug(f"Waiting {wait_time} seconds before next PNL check for CA {ca} ({context})")
            await asyncio.sleep(wait_time)
            logger.debug(f"Finished waiting {wait_time} seconds for CA {ca} ({context})")

    logger.info(f"Completed PNL report generation ({context})")

# Initialize PNL report enabled flag
pnl_report_enabled = True

from aiogram import types
from aiogram.filters import Command

@dp.message(Command(commands=['runpnlreport']))
async def run_pnl_report_on_demand(message: types.Message):
    # Get the username of the user who sent the command
    username = message.from_user.username
    if not username:
        await message.reply("You must have a username set to use this command.")
        logger.warning(f"User {message.from_user.id} (no username) attempted to run /runpnlreport")
        return

    # Restrict command to authorized users
    if f"@{username}" not in authorized_users:
        await message.reply("You are not authorized to run this command.")
        logger.warning(f"Unauthorized user @{username} ({message.from_user.id}) attempted to run /runpnlreport")
        return

    logger.info(f"User @{username} ({message.from_user.id}) triggered on-demand PNL report generation")
    await message.reply("Starting on-demand PNL report generation...")

    # Check if a PNL report is already running (if using pnl_running event)
    if 'pnl_running' in globals() and pnl_running.is_set():
        await message.reply("A PNL report is already running. Please wait for it to complete.")
        logger.warning("On-demand PNL report aborted: another report is already running")
        return

    try:
        # Run the existing PNL report generation logic
        await generate_pnl_report(context="on-demand")
        await message.reply("On-demand PNL report generation completed successfully.")
    except Exception as e:
        logger.error(f"Error during on-demand PNL report generation: {e}")
        await message.reply(f"Error during PNL report generation: {str(e)}")
        

# Handler for /getchatid to get chat id
@dp.message(Command(commands=["getchatid"]))
async def get_chat_id(message: types.Message):
    logger.info(f"Chat ID: {message.chat.id}")
    await message.answer(f"Chat ID: {message.chat.id}")
    
# Handler for /mastersetup command to display all filter settings
@dp.message(Command(commands=["mastersetup"]))
async def master_setup(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /mastersetup command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /mastersetup attempt by @{username}")
        return
    response = "📋 **Master Setup - Current Filter Configurations**\n\n"
    
    response += "🔧 **Filter Toggles**\n"
    response += f"- Filter Enabled: {filter_enabled}\n"
    response += f"- CheckHigh Enabled: {CheckHighEnabled}\n"
    response += f"- CheckLow Enabled: {CheckLowEnabled}\n"
    response += f"- DevSold Filter Enabled: {DevSoldFilterEnabled}\n"
    response += f"- Top10 Filter Enabled: {Top10FilterEnabled}\n"
    response += f"- Snipers Filter Enabled: {SniphersFilterEnabled}\n"
    response += f"- Bundles Filter Enabled: {BundlesFilterEnabled}\n"
    response += f"- Insiders Filter Enabled: {InsidersFilterEnabled}\n"
    response += f"- KOLs Filter Enabled: {KOLsFilterEnabled}\n"
    response += f"- PNL Images Enabled: {pnl_report_enabled}\n"
    response += f"- Growth Notifications Enabled: {growth_notifications_enabled}\n\n"

    response += "📊 **Threshold Settings**\n"
    pass_value_str = str(PassValue) if PassValue is not None else "Not set"
    range_low_str = str(RangeLow) if RangeLow is not None else "Not set"
    dev_sold_threshold_str = str(DevSoldThreshold) if DevSoldThreshold is not None else "Not set"
    dev_sold_left_str = str(DevSoldLeft) if DevSoldLeft is not None else "Not set"
    top_10_threshold_str = str(Top10Threshold) if Top10Threshold is not None else "Not set"
    snipers_threshold_str = str(SnipersThreshold) if SnipersThreshold is not None else "Not set"
    bundles_threshold_str = str(BundlesThreshold) if BundlesThreshold is not None else "Not set"
    insiders_threshold_str = str(InsidersThreshold) if InsidersThreshold is not None else "Not set"
    kols_threshold_str = str(KOLsThreshold) if KOLsThreshold is not None else "Not set"

    def escape_markdown(text):
        special_chars = r'\*_`\[\]\(\)#\+-=!|{}\.%'
        return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', text)

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
    
    current_offset = len(response.encode('utf-8'))
    for i, line in enumerate(lines):
        logger.info(f"Line {i+1} byte offset: {current_offset} - {line.strip()}")
        response += line
        current_offset += len(line.encode('utf-8'))

    response += "\n🔍 Use the respective /set* and /filter commands to adjust these settings."

    logger.info(f"Full master setup response: {response}")
    try:
        logger.info(f"Sending master setup response: {response[:100]}...")
        await message.answer(response, parse_mode="Markdown")
        logger.info("Master setup response sent successfully")
    except Exception as e:
        logger.error(f"Failed to send master setup response: {e}")
        logger.info("Retrying without Markdown parsing...")
        await message.answer(response, parse_mode=None)
        logger.info("Sent response without Markdown parsing as a fallback")

# Handler for /resetdefaults command
@dp.message(Command(commands=["resetdefaults"]))
async def reset_defaults(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /resetdefaults command from user: @{username}")
    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /resetdefaults attempt by @{username}")
        return
    global filter_enabled, CheckHighEnabled, CheckLowEnabled, PassValue, RangeLow
    global DevSoldThreshold, DevSoldLeft, DevSoldFilterEnabled, Top10Threshold, Top10FilterEnabled
    global SnipersThreshold, SniphersFilterEnabled, BundlesThreshold, BundlesFilterEnabled
    global InsidersThreshold, InsidersFilterEnabled, KOLsThreshold, KOLsFilterEnabled
    global growth_notifications_enabled
    # Set defaults (adjust these based on your initial values in Chunk 1)
    filter_enabled = True
    CheckHighEnabled = False
    CheckLowEnabled = False
    PassValue = 1.5
    RangeLow = 1.0
    DevSoldThreshold = "No"
    DevSoldLeft = 10.0
    DevSoldFilterEnabled = False
    Top10Threshold = 20.0
    Top10FilterEnabled = False
    SnipersThreshold = 3.0
    SniphersFilterEnabled = False
    BundlesThreshold = 1.0
    BundlesFilterEnabled = False
    InsidersThreshold = 10.0
    InsidersFilterEnabled = False
    KOLsThreshold = 1.0
    KOLsFilterEnabled = False
    growth_notifications_enabled = False
    await message.answer("All settings have been reset to default values ✅")
    logger.info(f"All settings reset to defaults by @{username}")

@app.route('/download/<filename>')
def download_file(filename):
    token = request.args.get('token')
    if token != DOWNLOAD_TOKEN:
        logger.warning(f"Invalid download token: {token}, expected: {DOWNLOAD_TOKEN}")
        abort(403, description="Invalid or missing token")
    
    allowed_files = [
        "public_ca_filter_log.csv",
        "vip_ca_filter_log.csv",
        "public_growthcheck_log.csv",
        "vip_growthcheck_log.csv",
        "monitored_tokens.csv"
    ]
    if filename not in allowed_files:
        logger.error(f"Requested file {filename} not in allowed list")
        abort(404, description="File not found")
    
    file_path = os.path.join("/app/data", filename)
    logger.debug(f"Checking file at {file_path}: exists={os.path.exists(file_path)}, size={os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'}")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found for download: {file_path}")
        abort(404, description="File does not exist")
    
    logger.info(f"Serving file: {file_path}")
    return send_file(file_path, as_attachment=True)

def is_authorized(username):
    logger.info(f"Checking authorization for @{username}: {f'@{username}' in authorized_users}")
    return f"@{username}" in authorized_users  

# Scheduler and startup setup
async def on_startup():
    init_csv()
    load_monitored_tokens()
    commands = [
        BotCommand(command="test", description="Test the bot"),
        BotCommand(command="setfilter", description="Enable or disable the filter (Yes/No)"),
        BotCommand(command="setpassvalue", description="Set PassValue for CheckHigh (e.g., /setpassvalue 1.2)"),
        BotCommand(command="setrangelow", description="Set RangeLow for CheckLow (e.g., /setrangelow 1.1)"),
        BotCommand(command="setcheckhigh", description="Enable/disable CheckHigh filter (Yes/No)"),
        BotCommand(command="setchecklow", description="Enable/disable CheckLow filter (Yes/No)"),
        BotCommand(command="setdevsoldthreshold", description="Set DevSold threshold (Yes/No)"),
        BotCommand(command="setdevsoldleft", description="Set DevSoldLeft threshold (e.g., /setdevsoldleft 10)"),
        BotCommand(command="setdevsoldfilter", description="Enable/disable DevSold filter (Yes/No)"),
        BotCommand(command="settop10threshold", description="Set Top10 threshold (e.g., /settop10threshold 20)"),
        BotCommand(command="settop10filter", description="Enable/disable Top10 filter (Yes/No)"),
        BotCommand(command="setsnipersthreshold", description="Set Snipers threshold (e.g., /setsnipersthreshold 3 or None)"),
        BotCommand(command="setsnipersfilter", description="Enable/disable Snipers filter (Yes/No)"),
        BotCommand(command="setbundlesthreshold", description="Set Bundles threshold (e.g., /setbundlesthreshold 1)"),
        BotCommand(command="setbundlesfilter", description="Enable/disable Bundles filter (Yes/No)"),
        BotCommand(command="setinsidersthreshold", description="Set Insiders threshold (e.g., /setinsidersthreshold 10 or None)"),
        BotCommand(command="setinsidersfilter", description="Enable/disable Insiders filter (Yes/No)"),
        BotCommand(command="setkolsthreshold", description="Set KOLs threshold (e.g., /setkolsthreshold 1)"),
        BotCommand(command="setkolsfilter", description="Enable/disable KOLs filter (Yes/No)"),
        BotCommand(command="adduser", description="Add an authorized user (only for @BeingHumbleGuy)"),
        BotCommand(command="ca", description="Get token data (e.g., /ca <token_ca>)"),
        BotCommand(command="downloadcsv", description="Get link to download CA filter CSV log"),
        BotCommand(command="downloadgrowthcsv", description="Get link to download growth check CSV log"),
        BotCommand(command="growthnotify", description="Enable/disable growth notifications (Yes/No)"),
        BotCommand(command="mastersetup", description="Display all current filter settings"),
        BotCommand(command="resetdefaults", description="Reset all settings to default values"),
        BotCommand(command="downloadmonitoredtokens", description="Get link to download monitored tokens CSV"),
        BotCommand(command="setpnlreport", description="Enable/disable PNL report generation (Yes/No)"),
        BotCommand(command="getchatid", description="Get Chat ID"),
        BotCommand(command="runpnlreport", description="Run PNL report")
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Successfully set bot commands for suggestions")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

    # Set up the scheduler for growthcheck and daily_summary_report
    logger.debug("Starting scheduler")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(growthcheck, 'interval', seconds=CHECK_INTERVAL)
    logger.debug(f"Scheduled growthcheck job every {CHECK_INTERVAL} seconds")
    scheduler.add_job(daily_summary_report, 'interval', seconds=DAILY_REPORT_INTERVAL)
    logger.debug(f"Scheduled daily_summary_report job every {DAILY_REPORT_INTERVAL} seconds")
    scheduler.add_job(generate_pnl_report, 'interval', seconds=PNL_REPORT_INTERVAL, max_instances=1)
    logger.debug(f"Scheduled generate_pnl_report job every {PNL_REPORT_INTERVAL} seconds with 1-hour execution window")
    scheduler.start()
    logger.debug("Scheduler started")

async def on_shutdown():
    logger.info("Shutting down bot...")
    await bot.session.close()
    await dp.storage.close()
    logger.info("Bot shutdown complete.")

# Flask route to handle OAuth callback with token exchange
@app.route('/api/auth/callback/twitter', methods=['GET'])
def handle_callback():
    code = request.args.get('code')
    if code:
        logger.debug(f"Received OAuth code: {code}")
        client_id = os.getenv("X_CLIENT_ID")
        client_secret = os.getenv("X_CLIENT_SECRET")
        code_verifier = os.getenv("X_CODE_VERIFIER")
        redirect_uri = "https://humbletechbot-production.up.railway.app/api/auth/callback/twitter"
        auth_string = f"{client_id}:{client_secret}"
        auth_header = base64.b64encode(auth_string.encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier
        }
        response = requests.post("https://api.twitter.com/2/oauth2/token", data=data, headers=headers)
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data["access_token"]
            os.environ["X_ACCESS_TOKEN"] = access_token  # Temporary local set
            logger.info(f"Obtained access token: {access_token}")
            return jsonify({"message": "Access token obtained", "access_token": access_token}), 200
        else:
            error_text = response.text
            logger.error(f"Token exchange failed: {response.status_code} - {error_text}")
            return jsonify({"error": "Token exchange failed", "details": error_text}), response.status_code
    return jsonify({"error": "No code parameter found"}), 400

async def main():
    try:
        await on_startup()
        port = int(os.getenv("PORT", 8080))
        flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False))
        flask_thread.start()
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())

# Chunk 6b ends

# Chunk 6 ends

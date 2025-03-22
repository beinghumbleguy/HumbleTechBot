# Chunk 1 starts
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity, BotCommand
from aiogram.filters import Command, BaseFilter
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
import time
import random
import aiohttp
import tls_client
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict
from cachetools import TTLCache
import pytz

# Chunk 1 starts

from aiogram.filters import BaseFilter
from aiogram import types

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


# Thread locks for safe CSV writing
csv_lock = threading.Lock()
growth_csv_lock = threading.Lock()
monitored_tokens_lock = threading.Lock()

# Thread pool executor for running blocking tasks
_executor = ThreadPoolExecutor(max_workers=5)

# Global variables with default values as specified
# Note: Default values can only be reset to their initial state by @BeingHumbleGuy or an additional user added via /adduser
filter_enabled = True
PassValue = 1.35
RangeLow = 1.07
authorized_users = ["@BeingHumbleGuy"]
additional_user_added = False

# BSRatio filter toggles
CheckHighEnabled = True
CheckLowEnabled = True

# New filter thresholds
DevSoldThreshold = "Yes"
DevSoldLeft = 5.0
Top10Threshold = 34.0
SnipersThreshold = None
BundlesThreshold = 8.0
InsidersThreshold = None
KOLsThreshold = 1.0

# New filter toggles
DevSoldFilterEnabled = True
Top10FilterEnabled = True
SniphersFilterEnabled = False
BundlesFilterEnabled = True
InsidersFilterEnabled = False
KOLsFilterEnabled = True

# Growth check variables
growth_notifications_enabled = True
GROWTH_THRESHOLD = 2.0
INCREMENT_THRESHOLD = 1.0
CHECK_INTERVAL = 300  # 5 minutes
MONITORING_DURATION = 21600  # 6 hours in seconds
monitored_tokens = {}
last_growth_ratios = {}

# CSV file paths for public and VIP channels
PUBLIC_CSV_FILE = "/app/data/public_ca_filter_log.csv"
VIP_CSV_FILE = "/app/data/vip_ca_filter_log.csv"
PUBLIC_GROWTH_CSV_FILE = "/app/data/public_growthcheck_log.csv"
VIP_GROWTH_CSV_FILE = "/app/data/vip_growthcheck_log.csv"
MONITORED_TOKENS_CSV_FILE = "/app/data/monitored_tokens.csv"

# Secret token for securing the Flask download route
DOWNLOAD_TOKEN = secrets.token_urlsafe(32)
logger.info(f"Generated download token: {DOWNLOAD_TOKEN}")

# Define VIP channels
VIP_CHANNEL_IDS = {-1002365061913}

# Initialize cache for API responses (TTL of 1 hour)
token_data_cache = TTLCache(maxsize=1000, ttl=3600)

# Initialize CSV files with headers if they don't exist
def init_csv():
    # Ensure the /app/data directory exists
    data_dir = "/app/data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Created directory: {data_dir}")

    # Filter CSV files
    for csv_file in [PUBLIC_CSV_FILE, VIP_CSV_FILE]:
        if not os.path.exists(csv_file):
            with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "CA", "BSRatio", "BSRatio_Pass", "BSRatio_Low_Pass",
                    "DevSold", "DevSoldLeftValue", "DevSold_Pass", "Top10", "Top10_Pass",
                    "Snipers", "Snipers_Pass", "Bundles", "Bundles_Pass", "Insiders", "Insiders_Pass",
                    "KOLs", "KOLs_Pass", "Overall_Pass", "MarketCap"
                ])
            logger.info(f"Created filter CSV file: {csv_file}")

    # Growth check CSV files
    for csv_file in [PUBLIC_GROWTH_CSV_FILE, VIP_GROWTH_CSV_FILE]:
        if not os.path.exists(csv_file):
            with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "ChatID", "ChannelID", "MessageID", "TokenName", "CA",
                    "OriginalMC", "CurrentMC", "GrowthRatio", "ProfitPercent", "TimeSinceAdded"
                ])
            logger.info(f"Created growth check CSV file: {csv_file}")

    # Monitored tokens CSV file
    if not os.path.exists(MONITORED_TOKENS_CSV_FILE):
        with open(MONITORED_TOKENS_CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "CA", "TokenName", "InitialMC", "Timestamp", "MessageID", "ChatID"
            ])
        logger.info(f"Created monitored tokens CSV file: {MONITORED_TOKENS_CSV_FILE}")

# Function to load monitored tokens from CSV on startup
def load_monitored_tokens():
    global monitored_tokens
    monitored_tokens = {}
    if os.path.exists(MONITORED_TOKENS_CSV_FILE):
        with open(MONITORED_TOKENS_CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ca = row["CA"]
                monitored_tokens[ca] = {
                    "token_name": row["TokenName"],
                    "initial_mc": float(row["InitialMC"]),
                    "timestamp": row["Timestamp"],
                    "message_id": int(row["MessageID"]),
                    "chat_id": int(row["ChatID"])
                }
        logger.info(f"Loaded {len(monitored_tokens)} tokens from {MONITORED_TOKENS_CSV_FILE}")
    else:
        logger.info(f"No monitored tokens CSV file found at {MONITORED_TOKENS_CSV_FILE}")

# Function to save monitored tokens to CSV
def save_monitored_tokens():
    with monitored_tokens_lock:
        with open(MONITORED_TOKENS_CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "CA", "TokenName", "InitialMC", "Timestamp", "MessageID", "ChatID"
            ])
            for ca, data in monitored_tokens.items():
                writer.writerow([
                    ca,
                    data["token_name"],
                    data["initial_mc"],
                    data["timestamp"],
                    data["message_id"],
                    data["chat_id"]
                ])
        logger.info(f"Saved {len(monitored_tokens)} tokens to {MONITORED_TOKENS_CSV_FILE}")

# Log filter results to the appropriate CSV based on channel type
def log_to_csv(ca, bs_ratio, bs_ratio_pass, check_low_pass, dev_sold, dev_sold_left_value, dev_sold_pass,
               top_10, top_10_pass, snipers, snipers_pass, bundles, bundles_pass,
               insiders, insiders_pass, kols, kols_pass, overall_pass, market_cap, is_vip_channel):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    csv_file = VIP_CSV_FILE if is_vip_channel else PUBLIC_CSV_FILE
    with csv_lock:
        with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
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
                overall_pass,
                market_cap if market_cap else "N/A"
            ])
    logger.info(f"Logged filter results to {csv_file} for CA: {ca}")

# Log growth check results to the appropriate CSV based on channel type
def log_to_growthcheck_csv(chat_id, channel_id, message_id, token_name, ca, original_mc, current_mc,
                           growth_ratio, profit_percent, time_since_added, is_vip_channel):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    csv_file = VIP_GROWTH_CSV_FILE if is_vip_channel else PUBLIC_GROWTH_CSV_FILE
    with growth_csv_lock:
        with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, chat_id, channel_id, message_id, token_name, ca,
                original_mc, current_mc, growth_ratio, profit_percent, time_since_added
            ])
    logger.info(f"Logged growth check to {csv_file} for CA: {ca}")

# Helper function to parse market cap string to float
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

# Helper function to format market cap for display
def format_market_cap(mc):
    if mc is None or mc == 0:
        return "N/A"
    if mc >= 1000000:
        return f"{mc/1000000:.1f}M"
    elif mc >= 1000:
        return f"{mc/1000:.1f}K"
    else:
        return f"{mc:.0f}"

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

# Chunk 1 ends

# Chunk 2 starts
# Session management for API requests
class APISessionManager:
    def __init__(self):
        self.session = None
        self.aio_session = None
        self._active_sessions = set()
        self._session_created_at = 0
        self._session_requests = 0
        self._session_max_age = 3600  # 1 hour
        self._session_max_requests = 100
        self.max_retries = 3
        self.retry_delay = 5  # Increased to 5 seconds
        self.base_url = "https://gmgn.ai"
        self._executor = _executor

        # Default headers
        self.headers_dict = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        self.custom_headers_dict = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Upgrade-Insecure-Requests": "1",
        }

        # Proxy list (formatted as username:password@host:port)
        raw_proxies = [
            "residential.birdproxies.com:7777:pool-p1-cc-us:sf3lefz1yj3zwjvy",
            # Add more proxies here if available, e.g.:
            # "proxy2.example.com:8080:username:password",
        ]
        self.proxy_list = []
        for proxy in raw_proxies:
            host, port, username, password = proxy.split(":")
            formatted_proxy = f"{username}:{password}@{host}:{port}"
            self.proxy_list.append(formatted_proxy)
        self.current_proxy_index = 0
        logger.info(f"Initialized proxy list with {len(self.proxy_list)} proxies")

    async def get_proxy_url(self):
        if not self.proxy_list:
            logger.warning("No proxies available in the proxy list")
            return None
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        logger.debug(f"Selected proxy: {proxy}")
        return proxy

    def update_proxy_list(self, proxy: str, append: bool = True):
        try:
            host, port, username, password = proxy.split(":")
            formatted_proxy = f"{username}:{password}@{host}:{port}"
        except ValueError:
            logger.error(f"Invalid proxy format: {proxy}. Expected host:port:username:password")
            return False

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
            if self.aio_session and not self.aio_session.closed:
                try:
                    await self.aio_session.close()
                    logger.debug(f"Closed aiohttp session {id(self.aio_session)}")
                except Exception as e:
                    logger.error(f"Error closing aiohttp session: {str(e)}")
                self.aio_session = None
                
            browser_names = [name for name in tls_client.settings.ClientIdentifiers.__args__ 
                            if name.startswith(('chrome', 'safari', 'firefox', 'opera'))]
            identifier = random.choice(browser_names)
            
            self.session = tls_client.Session(
                client_identifier=identifier,
                random_tls_extension_order=True
            )
            
            user_agent = UserAgent().random
            self.headers_dict["User-Agent"] = user_agent
            self.session.headers.update(self.headers_dict)
            
            if use_proxy:
                proxy_url = await self.get_proxy_url()
                if proxy_url:
                    if not proxy_url.startswith('http'):
                        proxy_url = f'http://{proxy_url}'
                    self.session.proxies = {
                        'http': proxy_url,
                        'https': proxy_url
                    }
                    logger.debug(f"Successfully configured proxy {proxy_url}.")
                else:
                    logger.warning("No proxy available, proceeding without proxy.")
            else:
                self.session.proxies = None
                logger.debug("Proceeding without proxy as per request.")
            
            connector = aiohttp.TCPConnector(ssl=False)
            self.aio_session = aiohttp.ClientSession(
                connector=connector,
                headers=self.headers_dict,
                trust_env=False
            )
            self._active_sessions.add(self.aio_session)
            logger.debug(f"Created new aiohttp session {id(self.aio_session)}")
            
            self._session_created_at = current_time
            self._session_requests = 0
            logger.debug("Created new TLS client session")

    async def _run_in_executor(self, func, *args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(
            self._executor, 
            lambda: func(*args, **kwargs)
        )

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> str:
        url = f"{self.base_url}/{endpoint}"
        logger.debug(f"Making request to: {url}")
        
        if self.session is None:
            await self.randomize_session()
        
        self._session_requests += 1
        
        # Try with proxy first
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    await self.randomize_session(force=True, use_proxy=True)
                logger.info(f"Attempt {attempt + 1} with proxy: {self.session.proxies}")
                response = await self._run_in_executor(
                    self.session.get,
                    url,
                    params=params,
                    allow_redirects=True
                )
                if response.status_code == 200:
                    return response.text
                logger.warning(f"TLS client attempt {attempt + 1} failed with status {response.status_code}")
            except Exception as e:
                logger.warning(f"TLS client attempt {attempt + 1} failed: {str(e)}")
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay)
        
        # Fallback: Try without proxy
        logger.info("All proxy attempts failed, trying without proxy as final fallback")
        await self.randomize_session(force=True, use_proxy=False)
        try:
            response = await self._run_in_executor(
                self.session.get,
                url,
                params=params,
                allow_redirects=True
            )
            if response.status_code == 200:
                return response.text
            logger.warning(f"Request without proxy failed with status {response.status_code}")
        except Exception as e:
            logger.error(f"Final attempt without proxy failed: {str(e)}")
        
        return ""

# Initialize API session manager
api_session_manager = APISessionManager()

# Updated function to get token data using API session manager
async def get_gmgn_token_data(mint_address):
    # Check cache first
    if mint_address in token_data_cache:
        logger.info(f"Returning cached data for CA: {mint_address}")
        return token_data_cache[mint_address]

    endpoint = f"sol/token/{mint_address}"
    try:
        html_content = await api_session_manager._make_request(endpoint)
        if not html_content:
            return {"error": "Failed to fetch data after retries."}

        soup = BeautifulSoup(html_content, "html.parser")
        token_data = {}
        try:
            # Fetch basic token data
            market_cap_str = soup.find("div", string="Market Cap").find_next_sibling("div").text.strip()
            token_data["market_cap"] = parse_market_cap(market_cap_str)
            token_data["market_cap_str"] = market_cap_str
            token_data["liquidity"] = soup.find("div", string="Liquidity").find_next_sibling("div").text.strip()
            token_data["price"] = soup.find("div", string="Price").find_next_sibling("div").text.strip()
            token_data["contract"] = mint_address

            # Attempt to fetch additional data points (adjust selectors based on actual HTML)
            buy_sell_section = soup.find("div", string=re.compile(r"Buy/Sell Ratio"))
            if buy_sell_section:
                bs_text = buy_sell_section.find_next_sibling("div").text.strip()
                bs_match = re.search(r'(\d+\.?\d*)/(\d+\.?\d*)', bs_text)
                if bs_match:
                    token_data["buy_percent"] = float(bs_match.group(1))
                    token_data["sell_percent"] = float(bs_match.group(2))

            dev_sold_section = soup.find("div", string=re.compile(r"Dev Sold"))
            if dev_sold_section:
                dev_text = dev_sold_section.find_next_sibling("div").text.strip()
                if "Yes" in dev_text:
                    token_data["dev_sold"] = "Yes"
                elif "left" in dev_text:
                    dev_left_match = re.search(r'(\d+\.?\d*)%\s*left', dev_text)
                    if dev_left_match:
                        token_data["dev_sold"] = "No"
                        token_data["dev_sold_left_value"] = float(dev_left_match.group(1))

            top_10_section = soup.find("div", string=re.compile(r"Top 10"))
            if top_10_section:
                top_10_text = top_10_section.find_next_sibling("div").text.strip()
                top_10_match = re.search(r'(\d+\.?\d*)', top_10_text)
                if top_10_match:
                    token_data["top_10"] = float(top_10_match.group(1))

            snipers_section = soup.find("div", string=re.compile(r"Sniper"))
            if snipers_section:
                snipers_text = snipers_section.find_next_sibling("div").text.strip()
                snipers_match = re.search(r'(\d+\.?\d*)', snipers_text)
                if snipers_match:
                    token_data["snipers"] = float(snipers_match.group(1))

            bundles_section = soup.find("div", string=re.compile(r"Bundle"))
            if bundles_section:
                bundles_text = bundles_section.find_next_sibling("div").text.strip()
                bundles_match = re.search(r'(\d+\.?\d*)', bundles_text)
                if bundles_match:
                    token_data["bundles"] = float(bundles_match.group(1))

            insiders_section = soup.find("div", string=re.compile(r"Insiders"))
            if insiders_section:
                insiders_text = insiders_section.find_next_sibling("div").text.strip()
                insiders_match = re.search(r'(\d+\.?\d*)', insiders_text)
                if insiders_match:
                    token_data["insiders"] = float(insiders_match.group(1))

            kols_section = soup.find("div", string=re.compile(r"KOLs"))
            if kols_section:
                kols_text = kols_section.find_next_sibling("div").text.strip()
                kols_match = re.search(r'(\d+\.?\d*)', kols_text)
                if kols_match:
                    token_data["kols"] = float(kols_match.group(1))

            # Cache the result
            token_data_cache[mint_address] = token_data
            logger.info(f"Cached token data for CA: {mint_address}")
            return token_data

        except AttributeError as e:
            logger.error(f"Failed to extract data for CA {mint_address}: {str(e)}")
            return {"error": "Failed to extract data. Structure may have changed."}
    except Exception as e:
        logger.error(f"Network error for CA {mint_address}: {str(e)}")
        return {"error": f"Network error: {str(e)}"}

# Function to fetch only the market cap for growth check
async def get_token_market_cap(mint_address):
    endpoint = f"sol/token/{mint_address}"
    try:
        html_content = await api_session_manager._make_request(endpoint)
        if not html_content:
            return {"error": "Failed to fetch data after retries."}

        soup = BeautifulSoup(html_content, "html.parser")
        market_cap_elem = soup.find("div", string="Market Cap")
        if not market_cap_elem:
            logger.error(f"Market Cap element not found for CA {mint_address}")
            return {"error": "Market Cap element not found in HTML"}
        market_cap_str = market_cap_elem.find_next_sibling("div").text.strip()
        market_cap = parse_market_cap(market_cap_str)
        return {"market_cap": market_cap}
    except Exception as e:
        logger.error(f"Error fetching market cap for CA {mint_address}: {str(e)}")
        return {"error": f"Network error: {str(e)}"}

# Chunk 2 ends

# Chunk 3 starts

from aiogram.filters import Command  # Ensure this is in Chunk 1 imports

# Chunk 3 starts
@dp.message(~Command(commands=[
    "test", "ca", "setfilter", "setpassvalue", "setrangelow", "setcheckhigh", 
    "setchecklow", "setdevsoldthreshold", "setdevsoldleft", "setdevsoldfilter", 
    "settop10threshold", "settop10filter", "setsnipersthreshold", "setsnipersfilter", 
    "setbundlesthreshold", "setbundlesfilter", "setinsidersthreshold", "setinsidersfilter", 
    "setkolsthreshold", "setkolsfilter", "adduser", "downloadcsv", "downloadgrowthcsv", 
    "growthnotify", "mastersetup", "resetdefaults"
]), F.text)
async def convert_link_to_button(message: types.Message) -> None:
    logger.info(f"Processing message in convert_link_to_button: '{message.text}'")
    if not message.text:
        return
    chat_id = message.chat.id
    message_id = message.message_id
    text = message.text
    is_vip_channel = chat_id in VIP_CHANNEL_IDS
    
    # Extract CA from the message
    ca_match = re.search(r'[A-Za-z0-9]{44}', text)
    if not ca_match:
        return
    ca = ca_match.group(0)

    # Check for keywords
    has_early = "Early" in text
    has_fasol = "Fasol" in text

    # Extract market cap from the message (e.g., "💎 C: 43.7k")
    mc_match = re.search(r'💎\s*C:\s*(\d+\.?\d*[KM]?)', text, re.IGNORECASE)
    original_mc = 0  # Default to 0 if market cap cannot be parsed
    market_cap_str = "N/A"
    if mc_match:
        mc_str = mc_match.group(1)
        try:
            original_mc = parse_market_cap(mc_str)
            market_cap_str = f"${original_mc / 1000:.1f}K" if original_mc is not None and original_mc > 0 else "N/A"
        except ValueError as e:
            logger.error(f"Failed to parse market cap '{mc_str}': {str(e)}")

    # If "Fasol" keyword is present, preserve original details and add buttons
    if has_fasol:
        # Extract the message details up to the CA
        ca_index = text.find(ca)
        if ca_index != -1:
            details = text[:ca_index].strip()  # Everything before the CA
        else:
            details = text.split('\n')[:5]  # Fallback: Take first 5 lines if CA isn't found
            details = '\n'.join(details).strip()

        # Prepare the output with details, CA, and buttons
        output_text = f"{details}\n🔗 CA: {ca}\n"

        # Add buttons
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌟🚀 Join VIP 🚀🌟", url="https://t.me/HumbleMoonshotsPay_bot?start=start")]
            if not is_vip_channel else [],  # Only include "Join VIP" in public channel
            [
                InlineKeyboardButton(text="Bloom", url=f"https://t.me/BloomSolana_bot?start=ref_humbleguy_ca_{ca}"),
                InlineKeyboardButton(text="Fasol", url=f"https://t.me/fasol_robot?start=ref_humbleguy_ca_{ca}"),
            ],
            [
                InlineKeyboardButton(text="Maestro", url=f"http://t.me/maestro?start={ca}-beinghumbleguy"),
                InlineKeyboardButton(text="Trojan", url=f"https://t.me/solana_trojanbot?start=r-beinghumbleguy-{ca}")
            ]
        ])

        # Calculate the offset for the CA in the output text
        ca_offset = output_text.find(ca)
        await message.reply(
            text=output_text,
            reply_markup=keyboard,
            reply_to_message_id=message_id,
            parse_mode="Markdown",
            entities=[
                MessageEntity(
                    type="code",
                    offset=ca_offset,
                    length=len(ca)
                )
            ]
        )

        # Add to monitored_tokens
        first_line = text.split('\n')[0].strip()
        monitored_tokens[ca] = {
            "token_name": first_line,
            "initial_mc": original_mc,
            "timestamp": datetime.now(pytz.timezone('America/Los_Angeles')).strftime("%Y-%m-%d %H:%M:%S"),
            "message_id": message_id,
            "chat_id": chat_id
        }
        save_monitored_tokens()  # Save to CSV after adding
        return  # Exit the function after handling "Fasol" token

    # If "Fasol" is not present but "Early" is, apply filter logic
    if not has_early:
        return  # Skip processing if neither "Fasol" nor "Early" is present

    # Initialize filter variables with defaults
    buy_percent = 0
    sell_percent = 0
    dev_sold = "N/A"
    dev_sold_left_value = None
    top_10 = 0
    snipers = 0
    bundles = 0
    insiders = 0
    kols = 0

    # Parse filter data from the message
    # Parse Buy/Sell percentages
    buy_sell_match = re.search(r'Sum 🅑:(\d+\.?\d*)% \| Sum 🅢:(\d+\.?\d*)%', text)
    if buy_sell_match:
        buy_percent = float(buy_sell_match.group(1))
        sell_percent = float(buy_sell_match.group(2))

    # Parse DevSold
    dev_sold_match = re.search(r'Dev:(✅|❌)\s*(?:\((\d+\.?\d*)%\s*left\))?', text)
    if dev_sold_match:
        dev_sold = "Yes" if dev_sold_match.group(1) == "✅" else "No"
        if dev_sold_match.group(2):
            dev_sold_left_value = float(dev_sold_match.group(2))

    # Parse Top 10
    top_10_match = re.search(r'Top 10:\s*(\d+\.?\d*)%', text)
    if top_10_match:
        top_10 = float(top_10_match.group(1))

    # Parse Snipers
    snipers_match = re.search(r'Sniper:\s*\d+\s*buy\s*(\d+\.?\d*)%', text)
    if snipers_match:
        snipers = float(snipers_match.group(1))

    # Parse Bundles
    bundles_match = re.search(r'Bundle:\s*\d+\s*buy\s*(\d+\.?\d*)%', text)
    if bundles_match:
        bundles = float(bundles_match.group(1))

    # Parse Insiders
    insiders_match = re.search(r'🐁Insiders:\s*(\d+)', text)
    if insiders_match:
        insiders = int(insiders_match.group(1))

    # Parse KOLs
    kols_match = re.search(r'🌟KOLs:\s*(\d+)', text)
    if kols_match:
        kols = int(kols_match.group(1))

    # Apply filters
    all_filters_pass = False
    filter_results = []

    # BSRatio filter
    bs_ratio = buy_percent / sell_percent if sell_percent != 0 else float('inf')
    bs_ratio_pass = False
    if CheckHighEnabled and bs_ratio >= PassValue:
        bs_ratio_pass = True
    elif CheckLowEnabled and 1 <= bs_ratio <= RangeLow:
        bs_ratio_pass = True
    filter_results.append(f"BSRatio: {bs_ratio:.2f} {'✅' if bs_ratio_pass else '🚫'} (Threshold: >= {PassValue} or 1 to {RangeLow})")

    # DevSold filter
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

    # Top10 filter
    top_10_pass = False
    if not Top10FilterEnabled:
        filter_results.append(f"Top10: {top_10} (Disabled)")
    else:
        top_10_pass = top_10 <= Top10Threshold
        filter_results.append(f"Top10: {top_10} {'✅' if top_10_pass else '🚫'} (Threshold: <= {Top10Threshold})")

    # Snipers filter
    if not SniphersFilterEnabled or SnipersThreshold is None:
        filter_results.append(f"Snipers: {snipers} (Disabled)")
        snipers_pass = True
    else:
        snipers_pass = snipers <= SnipersThreshold
        filter_results.append(f"Snipers: {snipers} {'✅' if snipers_pass else '🚫'} (Threshold: <= {SnipersThreshold})")

    # Bundles filter
    if not BundlesFilterEnabled:
        filter_results.append(f"Bundles: {bundles} (Disabled)")
        bundles_pass = True
    else:
        bundles_pass = bundles <= BundlesThreshold
        filter_results.append(f"Bundles: {bundles} {'✅' if bundles_pass else '🚫'} (Threshold: <= {BundlesThreshold})")

    # Insiders filter
    if not InsidersFilterEnabled or InsidersThreshold is None:
        filter_results.append(f"Insiders: {insiders} (Disabled)")
        insiders_pass = True
    else:
        insiders_pass = insiders <= InsidersThreshold
        filter_results.append(f"Insiders: {insiders} {'✅' if insiders_pass else '🚫'} (Threshold: <= {InsidersThreshold})")

    # KOLs filter
    if not KOLsFilterEnabled:
        filter_results.append(f"KOLs: {kols} (Disabled)")
        kols_pass = True
    else:
        kols_pass = kols >= KOLsThreshold
        filter_results.append(f"KOLs: {kols} {'✅' if kols_pass else '🚫'} (Threshold: >= {KOLsThreshold})")

    # Determine if all filters pass
    all_filters_pass = all([
        bs_ratio_pass,
        dev_sold_pass if DevSoldFilterEnabled else True,
        top_10_pass if Top10FilterEnabled else True,
        snipers_pass if SniphersFilterEnabled and SnipersThreshold is not None else True,
        bundles_pass if BundlesFilterEnabled else True,
        insiders_pass if InsidersFilterEnabled and InsidersThreshold is not None else True,
        kols_pass if KOLsFilterEnabled else True
    ])

    # Log filter results to CSV (always use PUBLIC_CSV_FILE for "Early" tokens)
    log_to_csv(
        ca=ca,
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
        overall_pass=all_filters_pass,
        market_cap=market_cap_str,
        is_vip_channel=False  # Always log "Early" tokens to PUBLIC_CSV_FILE
    )

    # Prepare and send the output message with filter results
    first_line = text.split('\n')[0].strip()
    output_text = f"{'CA qualified: ✅' if all_filters_pass else 'CA did not qualify: 🚫'}\n**{first_line}**\n**🔗 CA: {ca}**\n" + "\n".join(filter_results)

    await message.reply(
        text=output_text,
        parse_mode="Markdown",
        reply_to_message_id=message_id,
        entities=[
            MessageEntity(
                type="code",
                offset=output_text.index(ca),
                length=len(ca)
            )
        ]
    )
# Chunk 3 ends

# Chunk 4 starts
# Background task to monitor token market cap growth
async def growthcheck() -> None:
    current_time = datetime.now(pytz.timezone('America/Los_Angeles'))
    to_remove = []

    for ca, data in monitored_tokens.items():
        token_name = data["token_name"]
        initial_mc = data["initial_mc"]
        timestamp_str = data["timestamp"]
        message_id = data["message_id"]
        chat_id = data["chat_id"]

        # Parse the timestamp
        token_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.timezone('America/Los_Angeles'))
        time_diff = (current_time - token_time).total_seconds() / 3600  # Time difference in hours

        # Remove tokens older than 6 hours
        if time_diff > 6:
            to_remove.append(ca)
            continue

        # Fetch current market cap using API
        token_data = await get_token_market_cap(ca)
        if "error" in token_data:
            continue
        current_mc = token_data["market_cap"]
        if current_mc is None or current_mc == 0:
            continue

        # Calculate growth
        growth_ratio = current_mc / initial_mc if initial_mc != 0 else 0
        profit_percent = ((current_mc - initial_mc) / initial_mc) * 100 if initial_mc != 0 else 0

        # Check if growth meets the threshold
        last_growth_ratio = last_growth_ratios.get(ca, 1.0)
        if growth_ratio >= GROWTH_THRESHOLD and growth_ratio >= last_growth_ratio + INCREMENT_THRESHOLD:
            last_growth_ratios[ca] = growth_ratio

            # Log growth to CSV
            time_since_added = calculate_time_since(token_time.timestamp())
            is_vip_channel = chat_id in VIP_CHANNEL_IDS
            log_to_growthcheck_csv(
                chat_id=chat_id,
                channel_id=chat_id,
                message_id=message_id,
                token_name=token_name,
                ca=ca,
                original_mc=initial_mc,
                current_mc=current_mc,
                growth_ratio=growth_ratio,
                profit_percent=profit_percent,
                time_since_added=time_since_added,
                is_vip_channel=is_vip_channel
            )

            # Send growth notification as a reply to the original message
            if growth_notifications_enabled:
                initial_mc_str = f"${initial_mc / 1000:.1f}K" if initial_mc is not None and initial_mc > 0 else "N/A"
                current_mc_str = f"${current_mc / 1000:.1f}K" if current_mc is not None and current_mc > 0 else "N/A"
                growth_message = (
                    f"⚡ **{token_name} Pumps Hard!** 💎\n"
                    f"MC: {initial_mc_str} ➡ {current_mc_str} | 🚀 {growth_ratio:.1f}x | Profit: +{profit_percent:.1f}% | ⏳ {time_since_added}"
                )
                await bot.send_message(
                    chat_id=chat_id,
                    text=growth_message,
                    parse_mode="Markdown",
                    reply_to_message_id=message_id
                )

    # Remove expired tokens
    for ca in to_remove:
        monitored_tokens.pop(ca, None)
        last_growth_ratios.pop(ca, None)
    if to_remove:  # Only save if we removed tokens
        save_monitored_tokens()  # Save to CSV after removing

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

# Define the middleware with the correct signature
async def log_update(handler, event: types.Update, data: dict):
    logger.info(f"Raw update received: {event}")
    return await handler(event, data)  # Pass event and data to the next handler

# Register the middleware for all updates
dp.update.middleware(log_update)

# Test command handler
@dp.message(Command(commands=["test"]))
async def test_command(message: types.Message):
    try:
        username = message.from_user.username
        logger.info(f"Test command received from @{username}")
        await message.answer("Test command works!")
    except Exception as e:
        logger.error(f"Error in test_command: {e}")
        await message.answer(f"Error: {e}")

# Handler for /ca <token_ca> command
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
        else:
            price = float(token_data['price'].replace('$', ''))
            liquidity = parse_market_cap(token_data['liquidity'])
            liquidity_str = format_market_cap(liquidity)
            response = (
                f"Token Data for CA: {token_data['contract']}\n"
                f"📈 Market Cap: ${format_market_cap(token_data['market_cap'])}\n"
                f"💧 Liquidity: ${liquidity_str}\n"
                f"💰 Price: ${price:.6f}"
            )
            await message.reply(response)
    except Exception as e:
        logger.error(f"Error in cmd_ca: {e}")
        await message.answer(f"Error processing /ca: {e}")

# Handler for /setfilter command to toggle filter_enabled
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

# Handler for /downloadgrowthcsv command
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
    download_url = f"{base_url}/download/public_growthcheck_log.csv?token={DOWNLOAD_TOKEN}"
    if not os.path.exists("/app/data/public_growthcheck_log.csv"):
        await message.answer("⚠️ No growth check CSV file exists yet. Run some growth checks to generate data.")
        logger.info("Growth check CSV file not found for /downloadgrowthcsv")
        return
    await message.answer(
        f"Click the link to download or view the growth check CSV file:\n{download_url}\n"
        "Note: This link is private and should not be shared."
    )
    logger.info(f"Provided growth check CSV download link to @{username}: {download_url}")

# Handler for /growthnotify command
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

# Debug handler for all messages (moved to the end to catch unhandled messages)
@dp.message()
async def debug_all_messages(message: types.Message):
    try:
        logger.info(f"Received message in debug_all_messages: '{message.text}' from @{message.from_user.username} in chat {message.chat.id}")
    except Exception as e:
        logger.error(f"Error in debug_all_messages: {e}")

# Flask route for downloading CSV files
@app.route('/download/<filename>')
def download_file(filename):
    token = request.args.get('token')
    if token != DOWNLOAD_TOKEN:
        abort(403, description="Invalid or missing token")
    allowed_files = [
        "public_ca_filter_log.csv",
        "vip_ca_filter_log.csv",
        "public_growthcheck_log.csv",
        "vip_growthcheck_log.csv"
    ]
    if filename not in allowed_files:
        abort(404, description="File not found")
    file_path = os.path.join("/app/data", filename)
    if not os.path.exists(file_path):
        abort(404, description="File does not exist")
    return send_file(file_path, as_attachment=True)

# Function to check if a user is authorized
def is_authorized(username):
    logger.info(f"Checking authorization for @{username}: {f'@{username}' in authorized_users}")
    return f"@{username}" in authorized_users  

# Startup function to initialize CSV files, set bot commands, and schedule the growth check task
async def on_startup():
    init_csv()  # Initialize CSV files
    load_monitored_tokens()  # Load monitored tokens from CSV
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
        BotCommand(command="resetdefaults", description="Reset all settings to default values")
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Successfully set bot commands for suggestions")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")
    asyncio.create_task(schedule_growthcheck())

# Function to run the growth check periodically
async def schedule_growthcheck():
    while True:
        try:
            await growthcheck()
        except Exception as e:
            logger.error(f"Error in growthcheck: {e}")
        await asyncio.sleep(CHECK_INTERVAL)  # Run every 5 minutes

# Shutdown function to close bot sessions gracefully
async def on_shutdown():
    logger.info("Shutting down bot...")
    await bot.session.close()  # Close the bot's session
    await dp.storage.close()  # Close the storage (if using FSM)
    await dp.storage.wait_closed()
    logger.info("Bot shutdown complete.")

# Main function to start the bot
async def main():
    try:
        await on_startup()
        port = int(os.getenv("PORT", 8080))  # Match log output
        flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False))
        flask_thread.start()
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())
# Chunk 6 ends

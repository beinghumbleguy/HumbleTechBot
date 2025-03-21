# Chunk 1 starts
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
import time
import random
import aiohttp
import tls_client
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict
from cachetools import TTLCache  # For caching API responses
import pytz  # Added import for timezone handling

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

# Thread pool executor for running blocking tasks
_executor = ThreadPoolExecutor(max_workers=5)

# Global variables with default values as specified
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
monitored_tokens_lock = threading.Lock()
last_growth_ratios = {}  # Added to store last growth ratios

# CSV file paths for public and VIP channels
PUBLIC_CSV_FILE = "public_ca_filter_log.csv"
VIP_CSV_FILE = "vip_ca_filter_log.csv"
PUBLIC_GROWTH_CSV_FILE = "public_growthcheck_log.csv"
VIP_GROWTH_CSV_FILE = "vip_growthcheck_log.csv"

# Secret token for securing the Flask download route
DOWNLOAD_TOKEN = secrets.token_urlsafe(32)
logger.info(f"Generated download token: {DOWNLOAD_TOKEN}")

# Define VIP channels
VIP_CHANNEL_IDS = {-1002365061913}

# Initialize cache for API responses (TTL of 1 hour)
token_data_cache = TTLCache(maxsize=1000, ttl=3600)

# Initialize CSV files with headers if they don't exist
def init_csv():
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
    mc_str = mc_str.replace('$', '').replace(',', '').strip()
    if 'K' in mc_str:
        return float(mc_str.replace('K', '')) * 1000
    elif 'M' in mc_str:
        return float(mc_str.replace('M', '')) * 1000000
    else:
        return float(mc_str)

# Helper function to format market cap for display
def format_market_cap(mc):
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
        self.retry_delay = 2
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
            "residential.birdproxies.com:7777:pool-p1-cc-us:sf3lefz1yj3zwjvy",
            "residential.birdproxies.com:7777:pool-p1-cc-us:sf3lefz1yj3zwjvy",
            "residential.birdproxies.com:7777:pool-p1-cc-us:sf3lefz1yj3zwjvy",
            "residential.birdproxies.com:7777:pool-p1-cc-us:sf3lefz1yj3zwjvy",
            "residential.birdproxies.com:7777:pool-p1-cc-us:sf3lefz1yj3zwjvy",
            "residential.birdproxies.com:7777:pool-p1-cc-us:sf3lefz1yj3zwjvy",
            "residential.birdproxies.com:7777:pool-p1-cc-us:sf3lefz1yj3zwjvy",
            "residential.birdproxies.com:7777:pool-p1-cc-us:sf3lefz1yj3zwjvy",
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

    async def randomize_session(self, force: bool = False):
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
            
            proxy_url = await self.get_proxy_url()
            if proxy_url:
                if not proxy_url.startswith('http'):
                    proxy_url = f'http://{proxy_url}'
                self.session.proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                logger.debug(f"Successfully configured proxy {proxy_url}.")
            
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
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    await self.randomize_session(force=True)
                
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
                
        try:
            logger.info("Trying with alternative headers as final fallback")
            await self.randomize_session(force=True)
            
            self.session.headers.update(self.custom_headers_dict)
            
            response = await self._run_in_executor(
                self.session.get,
                url,
                params=params,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                return response.text
            
        except Exception as fallback_error:
            logger.error(f"Final fallback attempt failed: {str(fallback_error)}")
        
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
            market_cap_str = soup.find("div", text="Market Cap").find_next_sibling("div").text.strip()
            token_data["market_cap"] = parse_market_cap(market_cap_str)
            token_data["market_cap_str"] = market_cap_str
            token_data["liquidity"] = soup.find("div", text="Liquidity").find_next_sibling("div").text.strip()
            token_data["price"] = soup.find("div", text="Price").find_next_sibling("div").text.strip()
            token_data["contract"] = mint_address

            # Attempt to fetch additional data points (adjust selectors based on actual HTML)
            buy_sell_section = soup.find("div", text=re.compile(r"Buy/Sell Ratio"))
            if buy_sell_section:
                bs_text = buy_sell_section.find_next_sibling("div").text.strip()
                bs_match = re.search(r'(\d+\.?\d*)/(\d+\.?\d*)', bs_text)
                if bs_match:
                    token_data["buy_percent"] = float(bs_match.group(1))
                    token_data["sell_percent"] = float(bs_match.group(2))

            dev_sold_section = soup.find("div", text=re.compile(r"Dev Sold"))
            if dev_sold_section:
                dev_text = dev_sold_section.find_next_sibling("div").text.strip()
                if "Yes" in dev_text:
                    token_data["dev_sold"] = "Yes"
                elif "left" in dev_text:
                    dev_left_match = re.search(r'(\d+\.?\d*)%\s*left', dev_text)
                    if dev_left_match:
                        token_data["dev_sold"] = "No"
                        token_data["dev_sold_left_value"] = float(dev_left_match.group(1))

            top_10_section = soup.find("div", text=re.compile(r"Top 10"))
            if top_10_section:
                top_10_text = top_10_section.find_next_sibling("div").text.strip()
                top_10_match = re.search(r'(\d+\.?\d*)', top_10_text)
                if top_10_match:
                    token_data["top_10"] = float(top_10_match.group(1))

            snipers_section = soup.find("div", text=re.compile(r"Sniper"))
            if snipers_section:
                snipers_text = snipers_section.find_next_sibling("div").text.strip()
                snipers_match = re.search(r'(\d+\.?\d*)', snipers_text)
                if snipers_match:
                    token_data["snipers"] = float(snipers_match.group(1))

            bundles_section = soup.find("div", text=re.compile(r"Bundle"))
            if bundles_section:
                bundles_text = bundles_section.find_next_sibling("div").text.strip()
                bundles_match = re.search(r'(\d+\.?\d*)', bundles_text)
                if bundles_match:
                    token_data["bundles"] = float(bundles_match.group(1))

            insiders_section = soup.find("div", text=re.compile(r"Insiders"))
            if insiders_section:
                insiders_text = insiders_section.find_next_sibling("div").text.strip()
                insiders_match = re.search(r'(\d+\.?\d*)', insiders_text)
                if insiders_match:
                    token_data["insiders"] = float(insiders_match.group(1))

            kols_section = soup.find("div", text=re.compile(r"KOLs"))
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
        market_cap_str = soup.find("div", text="Market Cap").find_next_sibling("div").text.strip()
        market_cap = parse_market_cap(market_cap_str)
        return {"market_cap": market_cap}
    except Exception as e:
        logger.error(f"Error fetching market cap for CA {mint_address}: {str(e)}")
        return {"error": f"Network error: {str(e)}"}

# Chunk 2 ends

# Chunk 3 starts
@dp.message(F.text)
async def convert_link_to_button(message: types.Message) -> None:
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

    # Extract market cap from the message (without API call)
    original_mc = parse_market_cap(text)
    if original_mc is None:
        original_mc = 0  # Default to 0 if market cap cannot be parsed
    market_cap_str = f"${original_mc / 1000:.1f}K" if original_mc > 0 else "N/A"

    # If "Fasol" keyword is present, skip filter logic and only add buttons and monitoring
    if has_fasol:
        first_line = text.split('\n')[0].strip()
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
        await message.reply(
            text=f"Trade {first_line}",
            reply_markup=keyboard,
            reply_to_message_id=message_id
        )

        # Add to monitored_tokens
        monitored_tokens[ca] = {
            "token_name": first_line,
            "initial_mc": original_mc,
            "timestamp": datetime.now(pytz.timezone('America/Los_Angeles')).strftime("%Y-%m-%d %H:%M:%S"),
            "message_id": message_id,
            "chat_id": chat_id
        }
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
                type="pre",
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
                initial_mc_str = f"${initial_mc / 1000:.1f}K" if initial_mc > 0 else "N/A"
                current_mc_str = f"${current_mc / 1000:.1f}K" if current_mc > 0 else "N/A"
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

# Chunk 4 ends

# Chunk 5 starts (New Chunk)
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

# Chunk 5 ends

# Chunk 6 starts (Original Chunk 5)
# Handler for /growthnotify command to enable/disable growth notifications
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
    logger.info(f"Received /growthnotify command with text: {text}")

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

# Handler for /downloadcsv command
@dp.message(Command(commands=["downloadcsv"]))
async def download_csv(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /downloadcsv command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /downloadcsv attempt by @{username}")
        return

    public_url = f"http://localhost:5000/download/public_ca_filter_log.csv?token={DOWNLOAD_TOKEN}"
    vip_url = f"http://localhost:5000/download/vip_ca_filter_log.csv?token={DOWNLOAD_TOKEN}"
    await message.answer(
        f"📥 **Download CA Filter CSVs**\n\n"
        f"Public CSV: {public_url}\n"
        f"VIP CSV: {vip_url}",
        parse_mode="Markdown"
    )
    logger.info(f"Provided CSV download links to @{username}")

# Handler for /downloadgrowthcsv command
@dp.message(Command(commands=["downloadgrowthcsv"]))
async def download_growth_csv(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /downloadgrowthcsv command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /downloadgrowthcsv attempt by @{username}")
        return

    public_url = f"http://localhost:5000/download/public_growthcheck_log.csv?token={DOWNLOAD_TOKEN}"
    vip_url = f"http://localhost:5000/download/vip_growthcheck_log.csv?token={DOWNLOAD_TOKEN}"
    await message.answer(
        f"📥 **Download Growth Check CSVs**\n\n"
        f"Public Growth CSV: {public_url}\n"
        f"VIP Growth CSV: {vip_url}",
        parse_mode="Markdown"
    )
    logger.info(f"Provided Growth CSV download links to @{username}")

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
    
    file_path = filename
    if not os.path.exists(file_path):
        abort(404, description="File does not exist")
    
    return send_file(file_path, as_attachment=True)

# Function to check if a user is authorized
def is_authorized(username):
    return f"@{username}" in authorized_users  

# Chunk 6 ends

# Startup function to initialize CSV files and schedule the growth check task
async def on_startup():
    init_csv()  # Initialize CSV files
    # Schedule the growth check task
    asyncio.create_task(schedule_growthcheck())

# Function to run the growth check periodically
async def schedule_growthcheck():
    while True:
        await growthcheck()
        await asyncio.sleep(CHECK_INTERVAL)  # Run every 5 minutes

# Main function to start the bot
async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

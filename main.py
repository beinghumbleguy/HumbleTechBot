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
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict

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

# Thread lock for safe CSV writing
csv_lock = threading.Lock()

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

# CSV file path
CSV_FILE = "ca_filter_log.csv"

# Secret token for securing the Flask download route
DOWNLOAD_TOKEN = secrets.token_urlsafe(32)
logger.info(f"Generated download token: {DOWNLOAD_TOKEN}")

# Define VIP channels
VIP_CHANNEL_IDS = {-1002272066154, -1002280798125}

# Helper function to format numbers into K/M format
def format_number(value: float) -> str:
    """
    Convert a number into K (thousands) or M (millions) format.
    Example: 1234567 -> 1.23M, 4567 -> 4.57K, 123 -> 123
    """
    try:
        value = float(value)
        if value >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        elif value >= 1_000:
            return f"{value / 1_000:.2f}K"
        else:
            return f"{value:,.2f}"
    except (ValueError, TypeError):
        return "N/A"

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
        self.retry_delay = 5
        self.base_url = "https://gmgn.ai"
        self._executor = _executor

        # Default headers
        self.headers_dict = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://gmgn.ai/",
            "Origin": "https://gmgn.ai",
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

        # Proxy list
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
        """Update the proxy list by appending or replacing."""
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
        """Clear the proxy list."""
        self.proxy_list = []
        self.current_proxy_index = 0
        logger.info("Cleared proxy list")

    async def randomize_session(self, force: bool = False):
        """Create TLS client session with randomized fingerprint and headers."""
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
        """Run a blocking function in a thread pool."""
        return await asyncio.get_event_loop().run_in_executor(
            self._executor, 
            lambda: func(*args, **kwargs)
        )

    async def _make_request(self, endpoint: str, method: str = "GET", params: Optional[Dict] = None, data: Optional[Dict] = None) -> str:
        """Make a request with retry mechanism using TLS client in a non-blocking way."""
        url = f"{self.base_url}/{endpoint}"
        logger.debug(f"Making {method} request to: {url}")
        
        if self.session is None:
            await self.randomize_session()
        
        self._session_requests += 1
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    await self.randomize_session(force=True)
                
                if method.upper() == "POST":
                    response = await self._run_in_executor(
                        self.session.post,
                        url,
                        json=data,
                        headers=self.headers_dict,
                        params=params,
                        allow_redirects=True
                    )
                else:
                    response = await self._run_in_executor(
                        self.session.get,
                        url,
                        params=params,
                        allow_redirects=True
                    )
                
                if response.status_code == 200:
                    return response.text
                
                logger.warning(f"TLS client attempt {attempt + 1} failed with status {response.status_code}. Response: {response.text[:500]}...")
                
            except Exception as e:
                logger.warning(f"TLS client attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay)
                
        try:
            logger.info("Trying with alternative headers as final fallback")
            await self.randomize_session(force=True)
            
            self.session.headers.update(self.custom_headers_dict)
            
            if method.upper() == "POST":
                response = await self._run_in_executor(
                    self.session.post,
                    url,
                    json=data,
                    headers=self.custom_headers_dict,
                    params=params,
                    allow_redirects=True
                )
            else:
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

# Initialize CSV file with headers if it doesn't exist
def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "Token Name", "CA", "BSRatio", "BSRatio_Pass", "BSRatio_Low_Pass",
                "DevSold", "DevSoldLeftValue", "DevSold_Pass", "Top10", "Top10_Pass",
                "Snipers", "Snipers_Pass", "Bundles", "Bundles_Pass", "Insiders", "Insiders_Pass",
                "KOLs", "KOLs_Pass", "Overall_Pass"
            ])
        logger.info(f"Created CSV file: {CSV_FILE}")

# Log filter results to CSV
def log_to_csv(token_name, ca, bs_ratio, bs_ratio_pass, check_low_pass, dev_sold, dev_sold_left_value, dev_sold_pass,
               top_10, top_10_pass, snipers, snipers_pass, bundles, bundles_pass,
               insiders, insiders_pass, kols, kols_pass, overall_pass):
    timestamp = datetime.now().strftime("%Y-%m-d %H:%M:%S")
    with csv_lock:
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, token_name if token_name else "N/A", ca if ca else "N/A",
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
    logger.info(f"Logged filter results to CSV for Token: {token_name}, CA: {ca}")

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

# Function to get token data with K/M formatting (only for /ca command)
async def get_gmgn_token_data(mint_address):
    endpoint = "api/v1/mutil_window_token_info"
    logger.info(f"Fetching token data for CA: {mint_address} from endpoint: {endpoint}")
    
    payload = {
        "chain": "sol",
        "addresses": [mint_address]
    }
    
    try:
        response_text = await api_session_manager._make_request(
            endpoint,
            method="POST",
            data=payload
        )
        
        if not response_text:
            logger.error("Failed to fetch response after retries.")
            return {"error": "Failed to fetch data after retries."}

        logger.debug(f"Received response (first 500 chars): {response_text[:500]}...")
        
        try:
            response_json = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return {"error": f"Failed to parse API response: {str(e)}"}

        if not isinstance(response_json, dict) or "data" not in response_json:
            logger.error("Unexpected response format: 'data' key not found.")
            return {"error": "Unexpected response format from API."}

        token_data_list = response_json.get("data", [])
        if not token_data_list or not isinstance(token_data_list, list) or len(token_data_list) == 0:
            logger.error(f"No data found for address {mint_address} in response.")
            return {"error": f"No token data found for address {mint_address}."}

        token_data = token_data_list[0]
        if not token_data:
            logger.error(f"No data found for address {mint_address} in response.")
            return {"error": f"No token data found for address {mint_address}."}

        token_name = token_data.get("name", "Unknown Token")
        liquidity = token_data.get("liquidity", None)
        price = token_data.get("price", {}).get("price", None)
        circulating_supply = token_data.get("circulating_supply", None)

        if liquidity is None or price is None or circulating_supply is None:
            logger.error("Failed to extract all required fields. Extracted values: "
                         f"Liquidity={liquidity}, Price={price}, Circulating Supply={circulating_supply}")
            return {"error": "Failed to extract all required fields from API response."}

        try:
            price = float(price)
            circulating_supply = float(circulating_supply)
            market_cap = price * circulating_supply
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to calculate market cap: {str(e)}")
            return {"error": f"Failed to calculate market cap: {str(e)}"}

        # Format values using K/M format
        market_cap = format_number(market_cap)
        liquidity = format_number(liquidity) if liquidity else "N/A"
        circulating_supply = format_number(circulating_supply)
        price = f"${price:,.6f}"

        logger.info(f"Successfully extracted token data - Token Name: {token_name}, Market Cap: {market_cap}, Liquidity: {liquidity}, Circulating Supply: {circulating_supply}, Price: {price}")
        return {
            "token_name": token_name,
            "market_cap": market_cap,
            "liquidity": liquidity,
            "circulating_supply": circulating_supply,
            "price": price,
            "contract": mint_address
        }

    except Exception as e:
        logger.error(f"Error while fetching token data: {str(e)}")
        return {"error": f"Error: {str(e)}"}

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

# Handler for /setproxies command to manage proxy list
@dp.message(Command(commands=["setproxies"]))
async def set_proxies(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /setproxies command from user: @{username}")

    if not is_authorized(username):
        await message.answer("⚠️ You are not authorized to use this command.")
        logger.info(f"Unauthorized /setproxies attempt by @{username}")
        return

    text = message.text.lower().replace('/setproxies', '').strip()
    if not text:
        await message.answer("Usage: /setproxies <host:port:username:password> [append|replace] or /setproxies clear\n"
                             "Example: /setproxies residential.birdproxies.com:7777:pool-p1-cc-us:sf3lefz1yj3zwjvy append")
        logger.info("No proxy provided for /setproxies")
        return

    if text == "clear":
        api_session_manager.clear_proxy_list()
        await message.answer("Proxy list cleared ✅")
        logger.info("Proxy list cleared by user")
        return

    parts = text.split()
    if len(parts) < 1:
        await message.answer("Please provide a proxy in the format host:port:username:password")
        return

    proxy = parts[0]
    mode = parts[1] if len(parts) > 1 else "append"
    append = mode.lower() == "append"

    if api_session_manager.update_proxy_list(proxy, append=append):
        action = "Appended" if append else "Replaced"
        await message.answer(f"{action} proxy: {proxy} ✅\nCurrent proxy list size: {len(api_session_manager.proxy_list)}")
    else:
        await message.answer("⚠️ Invalid proxy format. Expected host:port:username:password")

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
        DevSoldThreshold = text.capitalize()
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

# Handler for /ca <token_ca> command with K/M formatting
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
        logger.warning(f"Error fetching token data: {token_data['error']}")
        await message.reply(f"Error: {token_data['error']}")
    else:
        response = (
            f"Token Data for {token_data['token_name']} (CA: {token_data['contract']})\n"
            f"📈 Market Cap: ${token_data['market_cap']}\n"
            f"💧 Liquidity: ${token_data['liquidity']}\n"
            f"💰 Price: {token_data['price']}\n"
            f"🔄 Circulating Supply: {token_data['circulating_supply']}"
        )
        logger.info(f"Sending response: {response}")
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
    response += f"- KOLs Filter Enabled: {KOLsFilterEnabled}\n\n"

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
    logger.info(f"Chat ID: {message.chat.id}")

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

    if not ca:
        ca_match = re.search(r'[A-Za-z0-9]{44}', text)
        if ca_match:
            ca = ca_match.group(0)
            logger.info(f"Extracted CA from plain text: {ca}")

    has_buy_sell = False
    buy_percent = None
    sell_percent = None
    dev_sold = None
    dev_sold_left_value = None
    top_10 = None
    snipers = None
    bundles = None
    insiders = None
    kols = None
    token_name = "Unknown Token"
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

        match_bundles = re.search(r'├?Bundles:\s*(\d+\.?\d*)', line)
        if match_bundles:
            bundles = float(match_bundles.group(1))
            logger.info(f"Found Bundles: {bundles}")
            continue

        match_insiders = re.search(r'├?Insiders:\s*(\d+\.?\d*)', line)
        if match_insiders:
            insiders = float(match_insiders.group(1))
            logger.info(f"Found Insiders: {insiders}")
            continue

        match_kols = re.search(r'├?KOLs:\s*(\d+\.?\d*)', line)
        if match_kols:
            kols = float(match_kols.group(1))
            logger.info(f"Found KOLs: {kols}")
            continue

        if not token_name or token_name == "Unknown Token":
            token_name_match = re.search(r'┌\s*(.*?)\s*┐', line)
            if token_name_match:
                token_name = token_name_match.group(1).strip()
                logger.info(f"Extracted Token Name: {token_name}")
                continue

    bs_ratio = None
    bs_ratio_pass = "N/A"
    check_low_pass = "N/A"
    dev_sold_pass = "N/A"
    top_10_pass = "N/A"
    snipers_pass = "N/A"
    bundles_pass = "N/A"
    insiders_pass = "N/A"
    kols_pass = "N/A"
    overall_pass = "N/A"

    if has_buy_sell and buy_percent is not None and sell_percent is not None:
        bs_ratio = buy_percent / (sell_percent + 0.0001)  # Avoid division by zero
        logger.info(f"Calculated B/S Ratio: {bs_ratio}")

        if CheckHighEnabled:
            bs_ratio_pass = bs_ratio >= PassValue
            logger.info(f"CheckHigh - B/S Ratio: {bs_ratio}, PassValue: {PassValue}, Pass: {bs_ratio_pass}")
        if CheckLowEnabled:
            check_low_pass = bs_ratio >= RangeLow
            logger.info(f"CheckLow - B/S Ratio: {bs_ratio}, RangeLow: {RangeLow}, Pass: {check_low_pass}")

    if DevSoldFilterEnabled and dev_sold is not None:
        if DevSoldThreshold.lower() == "yes":
            dev_sold_pass = dev_sold == "Yes"
        else:
            dev_sold_pass = dev_sold == "No" and (dev_sold_left_value is None or dev_sold_left_value >= DevSoldLeft)
        logger.info(f"DevSold Filter - DevSold: {dev_sold}, DevSoldLeft: {dev_sold_left_value}, Threshold: {DevSoldThreshold}, Pass: {dev_sold_pass}")

    if Top10FilterEnabled and top_10 is not None:
        top_10_pass = top_10 <= Top10Threshold
        logger.info(f"Top10 Filter - Top10: {top_10}, Threshold: {Top10Threshold}, Pass: {top_10_pass}")

    if SniphersFilterEnabled and snipers is not None and SnipersThreshold is not None:
        snipers_pass = snipers <= SnipersThreshold
        logger.info(f"Snipers Filter - Snipers: {snipers}, Threshold: {SnipersThreshold}, Pass: {snipers_pass}")

    if BundlesFilterEnabled and bundles is not None:
        bundles_pass = bundles <= BundlesThreshold
        logger.info(f"Bundles Filter - Bundles: {bundles}, Threshold: {BundlesThreshold}, Pass: {bundles_pass}")

    if InsidersFilterEnabled and insiders is not None and InsidersThreshold is not None:
        insiders_pass = insiders <= InsidersThreshold
        logger.info(f"Insiders Filter - Insiders: {insiders}, Threshold: {InsidersThreshold}, Pass: {insiders_pass}")

    if KOLsFilterEnabled and kols is not None:
        kols_pass = kols >= KOLsThreshold
        logger.info(f"KOLs Filter - KOLs: {kols}, Threshold: {KOLsThreshold}, Pass: {kols_pass}")

    all_filters = []
    if CheckHighEnabled or CheckLowEnabled:
        if CheckHighEnabled:
            all_filters.append(bs_ratio_pass == "N/A" or bs_ratio_pass)
        if CheckLowEnabled:
            all_filters.append(check_low_pass == "N/A" or check_low_pass)
    if DevSoldFilterEnabled:
        all_filters.append(dev_sold_pass == "N/A" or dev_sold_pass)
    if Top10FilterEnabled:
        all_filters.append(top_10_pass == "N/A" or top_10_pass)
    if SniphersFilterEnabled:
        all_filters.append(snipers_pass == "N/A" or snipers_pass)
    if BundlesFilterEnabled:
        all_filters.append(bundles_pass == "N/A" or bundles_pass)
    if InsidersFilterEnabled:
        all_filters.append(insiders_pass == "N/A" or insiders_pass)
    if KOLsFilterEnabled:
        all_filters.append(kols_pass == "N/A" or kols_pass)

    overall_pass = all(all_filters) if all_filters else "N/A"
    logger.info(f"Overall Pass: {overall_pass}, Filters applied: {all_filters}")

    log_to_csv(
        token_name=token_name,
        ca=ca,
        bs_ratio=bs_ratio,
        bs_ratio_pass=bs_ratio_pass,
        check_low_pass=check_low_pass,
        dev_sold=dev_sold,
        dev_sold_left_value=dev_sold_left_value,
        dev_sold_pass=dev_sold_pass,
        top_10=top_10,
        top_10_pass=top_10_pass,
        snipers=snipers,
        snipers_pass=snipers_pass,
        bundles=bundles,
        bundles_pass=bundles_pass,
        insiders=insiders,
        insiders_pass=insiders_pass,
        kols=kols,
        kols_pass=kols_pass,
        overall_pass=overall_pass
    )

    if filter_enabled and overall_pass is False and message.chat.id in VIP_CHANNEL_IDS:
        try:
            await message.delete()
            logger.info(f"Deleted message in VIP channel {message.chat.id} due to filter failure")
        except Exception as e:
            logger.error(f"Failed to delete message: {str(e)}")
        return

    if ca:
        button = InlineKeyboardButton(text="View on gmgn.ai", url=f"https://gmgn.ai/sol/token/{ca}")
        markup = InlineKeyboardMarkup(inline_keyboard=[[button]])
        try:
            await message.edit_text(text=message.text, reply_markup=markup, parse_mode=None, entities=message.entities)
            logger.info(f"Edited message with button for CA: {ca}")
        except Exception as e:
            logger.warning(f"Failed to edit message with button: {str(e)}. Attempting to send a new message.")
            try:
                await message.answer(text=message.text, reply_markup=markup, parse_mode=None, entities=message.entities)
                await message.delete()
                logger.info(f"Sent new message with button and deleted original for CA: {ca}")
            except Exception as e2:
                logger.error(f"Failed to send new message with button: {str(e2)}")

# Main function to start bot
async def main():
    logger.info("Starting bot polling...")
    # Initialize CSV file
    init_csv()
    # Start Flask in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    # Set bot commands
    commands = [
        BotCommand(command="ca", description="Get token data for a contract address"),
        BotCommand(command="filter", description="Enable/disable filter (Yes/No)"),
        BotCommand(command="checkhigh", description="Enable/disable CheckHigh filter (Yes/No)"),
        BotCommand(command="checklow", description="Enable/disable CheckLow filter (Yes/No)"),
        BotCommand(command="setupval", description="Set PassValue for CheckHigh"),
        BotCommand(command="setrangelow", description="Set RangeLow for CheckLow"),
        BotCommand(command="setdevsold", description="Set DevSold threshold (Yes/No)"),
        BotCommand(command="setdevsoldleft", description="Set DevSoldLeft percentage"),
        BotCommand(command="devsoldfilter", description="Enable/disable DevSold filter (Yes/No)"),
        BotCommand(command="settop10", description="Set Top10 threshold"),
        BotCommand(command="top10filter", description="Enable/disable Top10 filter (Yes/No)"),
        BotCommand(command="setsnipers", description="Set Snipers threshold"),
        BotCommand(command="snipersfilter", description="Enable/disable Snipers filter (Yes/No)"),
        BotCommand(command="setbundles", description="Set Bundles threshold"),
        BotCommand(command="bundlesfilter", description="Enable/disable Bundles filter (Yes/No)"),
        BotCommand(command="setinsiders", description="Set Insiders threshold"),
        BotCommand(command="insidersfilter", description="Enable/disable Insiders filter (Yes/No)"),
        BotCommand(command="setkols", description="Set KOLs threshold"),
        BotCommand(command="kolsfilter", description="Enable/disable KOLs filter (Yes/No)"),
        BotCommand(command="downloadcsv", description="Download the filter log CSV"),
        BotCommand(command="mastersetup", description="View all filter settings"),
        BotCommand(command="adduser", description="Add an authorized user (super user only)"),
        BotCommand(command="setproxies", description="Manage proxy list")
    ]
    await bot.set_my_commands(commands)
    logger.info("Bot commands set successfully")
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import logging
import os
import random
import time
import aiohttp
import tls_client
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN not set!")
    raise ValueError("BOT_TOKEN is required")

# Initialize Bot and Dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Thread pool executor
_executor = ThreadPoolExecutor(max_workers=5)

# API Session Manager
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
        self.base_url = "https://gmgn.ai/api/v1/mutil_window_token_info"
        
        # Proxy list
        self.proxy_list = [
            {
                "host": "residential.birdproxies.com",
                "port": 7777,
                "username": "pool-p1-cc-us",
                "password": "sf3lefz1yj3zwjvy"
            },
        ]
        self.current_proxy_index = 0
        
        # Default headers
        self.headers_dict = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://gmgn.ai/",
            "Origin": "https://gmgn.ai"
        }
    
    async def get_proxy(self):
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
        return proxy_url  # Comment out and return None to test without proxy
        # return None

    async def randomize_session(self, force: bool = False):
        """Create TLS client session with optimized headers."""
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
            
            self.session.headers.update(self.headers_dict)
            
            proxy_url = await self.get_proxy()
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
            _executor, 
            lambda: func(*args, **kwargs)
        )

    async def fetch_token_data(self, mint_address):
        """Fetch token data with retry mechanism."""
        await self.randomize_session()
        if not self.session or not self.aio_session:
            return {"error": "TLS client session not initialized"}
        
        self._session_requests += 1
        data = {"chain": "sol", "addresses": [mint_address]}
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.debug(f"Retrying with new session for attempt {attempt + 1}")
                    await self.randomize_session(force=True)
                
                response = await self._run_in_executor(
                    self.session.post,
                    self.base_url,
                    json=data,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    logger.debug("Success with tls_client")
                    return response.json()
                logger.warning(f"Attempt {attempt + 1} failed with status {response.status_code}. Response: {response.text[:500]}...")
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < self.max_retries - 1:
                logger.debug(f"Waiting {self.retry_delay} seconds before next attempt")
                await asyncio.sleep(self.retry_delay)
        
        return {"error": "Failed to fetch data after retries."}

# Initialize API session manager
api_session_manager = APISessionManager()

# Handler for /ca <token_ca> command
@dp.message(Command("ca"))
async def cmd_ca(message: types.Message):
    username = message.from_user.username
    logger.info(f"Received /ca command from {username}")

    text = message.text.split()
    if len(text) != 2:
        await message.answer("Usage: /ca <token_ca>")
        return

    token_ca = text[1].strip()
    logger.info(f"Fetching data for CA: {token_ca}")
    token_data = await api_session_manager.fetch_token_data(token_ca)

    if "error" in token_data:
        await message.reply(f"Error: {token_data['error']}")
    else:
        # Extract and calculate market cap
        data = token_data["data"][0]
        price = float(data["price"]["price"])
        circulating_supply = float(data["circulating_supply"])
        market_cap = price * circulating_supply
        
        # Format the response
        response = (
            f"**Token Data for {token_ca}**\n"
            f"📈 **{data['name']} ({data['symbol']})**\n"
            f"💰 Price: ${price:.6f} (24h: ${data['price']['price_24h']})\n"
            f"📉 Market Cap: ${market_cap:,.2f}\n"
            f"🌊 Liquidity: ${data['liquidity']}\n"
            f"📊 24h Volume: ${data['price']['volume_24h']}\n"
            f"👥 Holders: {data['holder_count']}\n"
            f"💸 Circulating Supply: {circulating_supply:,}\n"
            f"🔗 Logo: [View]({data['logo']})"
        )
        await message.reply(response, parse_mode="Markdown")

# Main function to start bot
async def main():
    logger.info("Starting bot polling...")
    dp.message.register(cmd_ca)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

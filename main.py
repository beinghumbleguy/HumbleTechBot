from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
import logging
import os
import aiohttp
import random
import time
import tls_client
from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent
from typing import Optional, Dict, Any

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
        self.retry_delay = 5  # Increased delay
        self.base_url = "https://gmgn.ai/api/v1/mutil_window_token_info"
        
        # Proxy list with explicit host, port, username, password
        self.proxy_list = [
            {
                "host": "residential.birdproxies.com",
                "port": 7777,
                "username": "pool-p1-cc-us",
                "password": "sf3lefz1yj3zwjvy"
            },
        ]
        self.current_proxy_index = 0
    
    async def get_proxy(self):
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
        return proxy_url  # Comment out and return None to test without proxy
        # return None

    async def randomize_session(self, force: bool = False):
        current_time = time.time()
        session_expired = (current_time - self._session_created_at) > self._session_max_age
        too_many_requests = self._session_requests >= self._session_max_requests

        if self.session is None or force or session_expired or too_many_requests:
            if self.aio_session and not self.aio_session.closed:
                try:
                    await self.aio_session.close()
                except Exception as e:
                    logger.error(f"Error closing aiohttp session: {str(e)}")
                self.aio_session = None

            try:
                browser_names = [name for name in tls_client.settings.ClientIdentifiers.__args__ 
                                if name.startswith(('chrome', 'safari', 'firefox', 'opera'))]
                identifier = random.choice(browser_names)
                
                self.session = tls_client.Session(
                    client_identifier=identifier,
                    random_tls_extension_order=True
                )
                
                user_agent = UserAgent().random
                self.session.headers.update({
                    "User-Agent": user_agent,
                    "Content-Type": "application/json",
                    # "Authorization": "Bearer YOUR_API_KEY"  # Uncomment and add key if required
                })
                
                proxy_url = await self.get_proxy()
                if proxy_url:
                    self.session.proxies = {
                        "http": proxy_url,
                        "https": proxy_url
                    }
                    logger.debug(f"Using proxy: {proxy_url}")
                
                connector = aiohttp.TCPConnector(ssl=False)
                self.aio_session = aiohttp.ClientSession(
                    connector=connector,
                    headers=self.session.headers,
                    trust_env=False
                )
                self._active_sessions.add(self.aio_session)
                
                self._session_created_at = current_time
                self._session_requests = 0
                logger.debug("Created new TLS client session")
            except Exception as e:
                logger.error(f"Failed to initialize TLS client session: {str(e)}")
                self.session = None
                self.aio_session = None

    async def _run_in_executor(self, func, *args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(_executor, lambda: func(*args, **kwargs))

    async def fetch_token_data(self, mint_address):
        await self.randomize_session()
        if not self.session or not self.aio_session:
            return {"error": "TLS client session not initialized"}
        
        self._session_requests += 1
        headers = self.session.headers
        payload = {"chain": "sol", "addresses": [mint_address]}
        
        for attempt in range(self.max_retries):
            try:
                async with self.aio_session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    proxy=self.session.proxies.get("http") if self.session.proxies else None,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    logger.warning(f"Attempt {attempt + 1} failed with status {response.status}")
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            
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
        response = f"Token Data for {token_ca}\n📈 Data: {token_data}"
        await message.reply(response)

# Main function to start bot
async def main():
    logger.info("Starting bot polling...")
    dp.message.register(cmd_ca)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

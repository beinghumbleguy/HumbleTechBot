from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
import logging
import os
import aiohttp
import random
import time
from concurrent.futures import ThreadPoolExecutor

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

# Thread pool executor
_executor = ThreadPoolExecutor(max_workers=5)

# API Session Manager
class APISessionManager:
    def __init__(self):
        self.aio_session = None
        self._session_created_at = 0
        self._session_requests = 0
        self._session_max_age = 3600  # 1 hour
        self._session_max_requests = 100
        self.max_retries = 3
        self.retry_delay = 2
        self.base_url = "https://gmgn.ai/api/v1/mutil_window_token_info"
        self.proxy_list = []
        self.current_proxy_index = 0
        
        # Static list of User-Agents
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        ]

    async def get_proxy(self):
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy

    async def randomize_session(self, force=False):
        current_time = time.time()
        session_expired = (current_time - self._session_created_at) > self._session_max_age
        too_many_requests = self._session_requests >= self._session_max_requests

        if not self.aio_session or force or session_expired or too_many_requests:
            if self.aio_session:
                await self.aio_session.close()
            self.aio_session = aiohttp.ClientSession()
            self._session_created_at = current_time
            self._session_requests = 0
            logger.info("Created new API session")

    async def fetch_token_data(self, mint_address):
        await self.randomize_session()
        self._session_requests += 1
        url = self.base_url
        headers = {
            "Content-Type": "application/json",
            "User-Agent": random.choice(self.user_agents)
        }
        payload = {"chain": "sol", "addresses": [mint_address]}
        
        for attempt in range(self.max_retries):
            try:
                async with self.aio_session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"API Response: {data}")
                        return data
                    else:
                        logger.warning(f"API request failed (Attempt {attempt + 1}): {response.status}")
            except Exception as e:
                logger.warning(f"Error in API request (Attempt {attempt + 1}): {str(e)}")
            await asyncio.sleep(self.retry_delay)

        return {"error": "Failed to fetch data after retries."}

# Initialize API session manager
api_session_manager = APISessionManager()

# Handler for /ca <token_ca> command
@dp.message(Command(commands=["ca"]))
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
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

from loguru import logger
from openai import AsyncOpenAI, OpenAI

from prompt_agent.configs import API_KEY, BASE_URL

# sync_client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

async_client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)

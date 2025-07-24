from loguru import logger
from tortoise import Tortoise

from prompt_agent.configs import DB_URL

# lifespan.py


async def init_db():
    await Tortoise.init(db_url=DB_URL, modules={"models": ["prompt_agent.models"]})
    await Tortoise.generate_schemas()
    logger.info(f"Tortoise-ORM started, database connected: {DB_URL}")

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from prompt_agent.db import init_db
from prompt_agent.periodic_checks.limit_sheduler import LimitScheduler
from prompt_agent.utils.time_zone_utils import set_cn_time_zone

# from rev_claude.client.client_manager import ClientManager


async def on_startup():
    logger.info("Lifespan Starting up")
    set_cn_time_zone()
    await init_db()  # Enable database initialization for our new models
    await LimitScheduler.start()


async def on_shutdown():
    logger.info("Lifespan Shutting down")
    await LimitScheduler.shutdown()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup()
    yield
    await on_shutdown()

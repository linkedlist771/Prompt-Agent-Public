from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from prompt_agent.configs import GROK_CLIENT_LIMIT_CHECKS_INTERVAL_MINUTES
from prompt_agent.periodic_checks.clients_limit_checks import \
    check_grok_clients_limits

limit_check_scheduler = AsyncIOScheduler()

# 设置定时任务
limit_check_scheduler.add_job(
    check_grok_clients_limits,
    trigger=IntervalTrigger(minutes=GROK_CLIENT_LIMIT_CHECKS_INTERVAL_MINUTES),
    id="check_usage_limits",
    name=f"Check API usage limits every {GROK_CLIENT_LIMIT_CHECKS_INTERVAL_MINUTES} minutes",
    replace_existing=True,
)


class LimitScheduler:
    limit_check_scheduler = limit_check_scheduler

    @staticmethod
    async def start():
        await check_grok_clients_limits()
        limit_check_scheduler.start()

    @staticmethod
    async def shutdown():
        limit_check_scheduler.shutdown()

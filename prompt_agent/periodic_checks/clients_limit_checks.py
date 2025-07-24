import asyncio
import multiprocessing
import sys
import time

from loguru import logger
# from prompt_agent.models import Cookie
# from prompt_agent.models.cookie_models import CookieQueries
# from prompt_agent.revgrok import GrokClient
from tqdm.asyncio import tqdm

#
#
# async def __check_grok_clients_limits():
#     start_time = time.perf_counter()
#     all_cookies = await Cookie.get_multi()
#     logger.info(f"Found {len(all_cookies)} cookies to check")
#
#     async def check_cookie(cookie):
#         try:
#             grok_client = GrokClient(cookie.cookie)
#             default_weights = {"DEFAULT": 0, "REASONING": 0, "DEEPSEARCH": 0}
#             rate_limit = await grok_client.get_rate_limit()
#
#             for kind, data in rate_limit.items():
#                 default_weights[kind] = data["remainingQueries"]
#
#             await CookieQueries.update_weights(cookie=cookie, weights=default_weights)
#             # logger.info(f"Cookie {cookie.id}: {default_weights}")
#
#             return f"Cookie {cookie.id}: {default_weights}"
#         except Exception as e:
#             from traceback import format_exc
#
#             logger.error(
#                 f"Error checking rate limit for cookie {cookie.id}: {format_exc()}"
#             )
#             return e
#
#     async def process_batch(batch):
#         return await asyncio.gather(*[check_cookie(cookie) for cookie in batch])
#
#     results = []
#     batch_size = 10  # 每批处理的客户端数量
#     total_batches = (len(all_cookies) + batch_size - 1) // batch_size
#
#     for i in range(0, len(all_cookies), batch_size):
#         batch = all_cookies[i : i + batch_size]
#         logger.info(f"Processing batch {i // batch_size + 1} of {total_batches}")
#         batch_results = await process_batch(batch)
#         results.extend(batch_results)
#         if i + batch_size < len(all_cookies):
#             logger.info("Waiting between batches...")
#             await asyncio.sleep(2)  # 批次之间的间隔
#
#     time_elapsed = time.perf_counter() - start_time
#     logger.debug(f"Time elapsed: {time_elapsed:.2f} seconds")
#     for result in results:
#         logger.info(result)


async def check_grok_clients_limits():
    ...
    # Use multiprocessing directly instead of ProcessPoolExecutor
    # process = multiprocessing.Process(target=run_grok_check)
    # process.daemon = True
    # process.start()
    #
    # logger.info("Grok clients check started in background process")
    # task = asyncio.create_task(__check_grok_clients_limits())

    # return {"message": "Grok clients check started in background process"}

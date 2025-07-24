import asyncio
from functools import wraps

from loguru import logger
from tqdm.asyncio import tqdm

REGISTER_MAY_RETRY = 1
REGISTER_MAY_RETRY_RELOAD = 15  # in reload there are more retries

REGISTER_WAIT = 3


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix) :].rstrip("\n")
    return text


def async_retry(retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    async for chunk in func(*args, **kwargs):
                        yield chunk
                    return
                except (RuntimeError, Exception) as e:
                    if attempt == retries - 1:  # Last attempt
                        logger.error(f"Failed after {retries} attempts: {str(e)}")
                        error_prefix = "[ERROR] "  # 添加错误前缀
                        if isinstance(e, RuntimeError):
                            yield error_prefix + str(e)
                        else:
                            from traceback import format_exc

                            logger.error(f"Error: {format_exc()}")
                            yield error_prefix + str(e)
                    else:
                        logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                        await asyncio.sleep(delay)

        return wrapper

    return decorator


@async_retry(retries=3, delay=1)
async def send_message_with_retry(poe_bot_client, bot, message, file_path):
    prefixes = []

    try:
        async for chunk in poe_bot_client.send_message(
            bot=bot,
            message=message,
            file_path=file_path,
        ):
            text = chunk["response"]

            # 检查是否是错误消息
            if text.startswith("[ERROR] "):
                # yield text  # 将错误消息 yield 出去
                raise RuntimeError(text)  # 抛出 RuntimeError
                # return  # 终止生成器

            # 如果文本为空，跳过这个chunk
            if not text:
                continue

            # 如果文本不是只有换行符，将其添加到prefixes列表
            if text.rstrip("\n"):
                prefixes.append(text.rstrip("\n"))

            # 如果已经有至少两个前缀，移除当前文本中的上一个前缀
            if len(prefixes) >= 2:
                text = remove_prefix(text, prefixes[-2])

            # yield处理后的文本
            yield text

    except Exception as e:
        # 捕获任何异常，将其转换为错误消息并 yield 出去
        error_message = (
            f"<think> {str(e)}</think>[ERROR] An unexpected error occurred: {str(e)}"
        )
        yield error_message
        # raise RuntimeError(f"An unexpected error occurred: {str(e)}")

from functools import lru_cache
from typing import Dict, List

import tiktoken
from loguru import logger
from revgrokapi.configs import DEFAULT_TOKENIZER


@lru_cache
def get_tokenizer():
    return tiktoken.get_encoding(DEFAULT_TOKENIZER)


def get_token_length(prompt: str) -> int:
    return len(get_tokenizer().encode(prompt))


def shorten_message_given_prompt_length(
    messages: List[Dict], token_limits: int
) -> List[Dict]:
    messages_str = "\n".join(
        [f"{message['role']}: {message['content']}" for message in messages]
    )
    token_length = get_token_length(messages_str)
    # logger.debug(f"Token length: {token_length}")
    # logger.debug(f"Token limits: {token_limits}")
    if token_length <= token_limits:
        return messages

    shortened_messages = messages.copy()

    # Keep removing non-system messages from the beginning until under token limit
    while len(shortened_messages) > 1:  # Keep at least one message
        # Find first non-system message
        remove_index = None
        for i, msg in enumerate(shortened_messages):
            if msg["role"] != "system":
                remove_index = i
                break

        if remove_index is None:
            break

        # Remove the message
        shortened_messages.pop(remove_index)

        # Check if we're now under the limit
        messages_str = "\n".join(
            [
                f"{message['role']}: {message['content']}"
                for message in shortened_messages
            ]
        )
        token_length = get_token_length(messages_str)
        if token_length <= token_limits:
            break

    return shortened_messages


if __name__ == "__main__":
    print(get_token_length("hello world"))

import re
import urllib.parse


def extract_cookie_value(cookie_str, key):
    # 构造正则表达式模式
    pattern = r"{}=([^;]+)".format(re.escape(key))

    # 正则匹配指定键的值
    match = re.search(pattern, cookie_str)
    if match:
        value = urllib.parse.unquote(match.group(1))
        return value
    else:
        return None

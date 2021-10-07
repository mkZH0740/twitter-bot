import hashlib
import json
import random
import urllib.parse

import aiohttp
import nonebot


async def get_screenshot_and_text(url: str):
    config = nonebot.get_driver().config
    server_url: str = config.server_url
    server_path: str = config.server_path
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{server_url}/screenshot', json={'url': url}) as response:
            if response.status != 200:
                return {
                    'type': 'err',
                    'message': f'服务器端错误{response.status}，请联系管理员'
                }
            server_response: dict[str, str] = await response.json(encoding='utf-8')
            response_type = server_response.get('type')
            if response_type == 'err':
                return {
                    'type': 'err',
                    'message': server_response.get('message')
                }
            elif response_type == 'ok':
                screenshot_path = server_response.get('screenshotPath')
                return {
                    'type': 'ok',
                    'text': server_response.get('text'),
                    'screenshot_path': f'{server_path}\\{screenshot_path}'
                }
            else:
                return {
                    'type': 'err',
                    'message': f'服务端未知回复{response_type}'
                }


async def get_translation(text: str):
    config = nonebot.get_driver().config
    translate_url = config.translate_url
    translate_appid = config.baidu_appid
    translate_secret = config.baidu_secret
    salt = random.randint(32768, 65536)
    sign = f'{translate_appid}{text}{salt}{translate_secret}'.encode('utf-8')
    md5_module = hashlib.md5()
    md5_module.update(sign)
    new_sign = md5_module.hexdigest()
    request_url = f'{translate_url}?q={urllib.parse.quote(text)}' \
                  f'&from=auto&to=zh&appid={translate_appid}&salt={salt}&sign={new_sign}'
    async with aiohttp.ClientSession() as session:
        async with session.get(request_url) as response:
            if response.status != 200:
                return f'翻译请求失败{response.status}'
            result: dict = await response.json(encoding='utf-8')
            if 'error_code' in result:
                return f'翻译请求失败{result["error_code"]}'
            translated_text = ''
            translated_results: list[dict[str, str]] = result.get('trans_result')
            for translated_result in translated_results:
                translated_text += translated_result['dst'] + '\n'
            return translated_text.strip()


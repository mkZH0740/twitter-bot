import aiohttp
import nonebot
import random
import hashlib
import urllib

from nonebot.plugin import require
from nonebot.adapters.cqhttp import MessageSegment

from aiohttp.client_exceptions import ClientError

from ..external import ExternalHolder


external = require('external')
external_holder: ExternalHolder = external.external_holder


async def get_screenshot_and_text(url: str, loaded_content: dict):
    config = nonebot.get_driver().config
    server_url: str = config.server_url
    server_path: str = config.server_path
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{server_url}/screenshot', json={'url': url}) as response:
                if response.status != 200:
                    loaded_content['text'] = f'请求失败{response.status}，请联系管理员'
                else:
                    server_response: dict = await response.json(encoding='utf-8')
                    match server_response:
                        case {'type': 'err', 'message': err_message}:
                            loaded_content['text'] = err_message
                        case {'type': 'ok', 'screenshotPath': screenshot_path, 'text': text}:
                            loaded_content['screenshot_path'] = f'{server_path}\\{screenshot_path}'
                            loaded_content['text'] = text
                        case _:
                            loaded_content['text'] = f'未知服务端响应{response}'
    except ClientError as e:
        await external_holder.reboot_server()
        loaded_content['text'] = f'服务器请求失败{e}'
    except Exception as e:
        loaded_content['text'] = f'其他错误{e}'


async def get_translation(text: str, loaded_content: dict):
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
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(request_url) as response:
                if response.status != 200:
                    loaded_content['translation'] = f'翻译请求失败{response.status}'
                else:
                    server_response: dict = await response.json(encoding='utf-8')
                    if 'error_code' in server_response:
                        loaded_content['translation'] = f'翻译请求失败{server_response["error_code"]}'
                    else:
                        translated_text = ''
                        translated_results: list[dict[str, str]] = server_response.get('trans_result')
                        for translated_result in translated_results:
                            translated_text += translated_result['dst'] + '\n'
                        loaded_content['translation'] = translated_text.strip()
    except ClientError as e:
        loaded_content['translation'] = f'服务器请求失败{e}'
    except Exception as e:
        loaded_content['translation'] = f'其他错误{e}'


async def make_forward_message_node(nickname: str, user_id: str, content: MessageSegment | str):
    return {
        'type': 'node',
        'data': {
            'name': nickname,
            'uin': user_id,
            'content': str(content)
        }
    }

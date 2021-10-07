from typing import Type

import aiofiles
import aiohttp
import nonebot
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp import GroupMessageEvent, MessageSegment

from ..db import BotDatabase, UserSetting
from ..db.models import custom_types


async def check_is_registered_group(matcher: Type[Matcher], event: GroupMessageEvent, bot_database: BotDatabase):
    group_setting = await bot_database.get_group_setting(event.group_id)
    if group_setting is None:
        await matcher.finish(f'群{event.group_id}未注册任何设置')
    return group_setting


async def check_args_length(matcher: Type[Matcher], event: GroupMessageEvent, sep: str, expected_length: int):
    args = str(event.get_message()).strip().split(sep)
    if len(args) != expected_length:
        await matcher.finish(f'非法参数长度，需要{expected_length}，当前{len(args)}')
    return args


async def check_custom_type(matcher: Type[Matcher], event: GroupMessageEvent, custom_key: str):
    custom_message = event.get_message()[0]
    if custom_key not in custom_types:
        await matcher.finish(f'未知自定义属性{custom_key}')
    if custom_message.type != custom_types[custom_key]:
        await matcher.finish(f'非法自定义类型，需要{custom_types[custom_key]}，当前{custom_message.type}')


async def save_image_to_path(url: str, path: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return False
            async with aiofiles.open(path, 'wb') as f:
                await f.write(await response.read())
            return True


async def matcher_switch_user_setting(matcher: Type[Matcher], event: GroupMessageEvent, bot_database: BotDatabase, value: bool):
    group_setting = await check_is_registered_group(matcher, event, bot_database)
    (screen_name, key) = await check_args_length(matcher, event, ';', 2)
    if screen_name == '*':
        results = await group_setting.switch_all_user_setting(key, value)
        result_message = ''
        for result in results:
            (curr_screen_name, flag, content) = result
            result_message += f'{curr_screen_name} -> {content}\n'
    else:
        result = await group_setting.switch_user_setting(key, value, screen_name=screen_name)
        result_message = f'{screen_name} -> {result[1]}'
    await matcher.finish(result_message.strip())


async def matcher_send_translation_screenshot(matcher: Type[Matcher], event: GroupMessageEvent, state):
    user_setting: UserSetting = state['user_setting']
    url: str = state['url']
    translation = str(event.get_message())
    config = nonebot.get_driver().config
    server_url: str = config.server_url
    server_path: str = config.server_path
    database_path: str = config.database_path
    default_tag_path = f'{database_path}\\default\\default_tag.png'
    default_css_path = f'{database_path}\\default\\default_css.css'
    request_payload = {
        'url': url,
        'translation': translation,
        'custom': {
            'tag': default_tag_path,
            'css': default_css_path,
            'background': ''
        }
    }
    if user_setting.custom_tag is not None:
        request_payload['custom']['tag'] = user_setting.custom_tag
    if user_setting.custom_css is not None:
        request_payload['custom']['css'] = user_setting.custom_css
    if user_setting.custom_background is not None:
        request_payload['custom']['background'] = user_setting.custom_background
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{server_url}/translate', json=request_payload) as response:
            if response.status != 200:
                await matcher.finish(f'服务端未知错误{response.status}，请联系管理员')
            else:
                result: dict[str, str] = await response.json()
                if result.get('type') == 'ok':
                    screenshot_path = f'{server_path}\\{result.get("screenshotPath")}'
                    await matcher.finish(MessageSegment.image(file=f'file:///{screenshot_path}'))
                elif result.get('type') == 'err':
                    message = result.get('message')
                    await matcher.finish(message)
                else:
                    await matcher.finish(f'服务器未知错误，请联系管理员')

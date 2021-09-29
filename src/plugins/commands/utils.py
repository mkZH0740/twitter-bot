from typing import Type

import aiofiles
import aiohttp
import nonebot
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp import GroupMessageEvent, MessageSegment

from ..database import BotDatabase
from ..database.models import Group, text_custom_settings, image_custom_settings


async def make_result_message(key: str, result: tuple[bool, str]):
    return result[1]


async def make_results_message(key: str, results: dict[str, tuple[bool, str]]):
    message = ''
    for screen_name, result in results.items():
        message += f'{screen_name}: {await make_result_message(key, result)}\n'
    return message.strip()


async def switch_group_setting(group: Group, target: str, key: str, value: bool):
    if target == '*':
        results = await group.modify_users(key, value)
        message = await make_results_message(key, results)
    else:
        result = await group.modify_user(target, key, value)
        message = await make_result_message(key, result)
    return message


async def matcher_switch_group_setting(matcher: Type[Matcher], bot_database: BotDatabase, event: GroupMessageEvent, value: bool):
    message = str(event.get_message()).strip()
    pair = message.split(';')
    if len(pair) != 2:
        await matcher.finish(f'invalid key value pair length {len(pair)}, expected 2')
    group_setting = await bot_database.get_group(event.group_id)
    if group_setting is None:
        await matcher.finish(f'unknown group {event.group_id}')
    key: str = pair[0]
    target: str = pair[1]
    if target != '*' and (await group_setting.get_user(target)) is None:
        await matcher.finish(f'unknown user {target}')
    result_message = await switch_group_setting(group_setting, target, key, value)
    await matcher.finish(result_message)


async def save_image_to_disk(url: str, path: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return False
            async with aiofiles.open(path, 'wb') as f:
                await f.write(await response.read())
            return True


async def matcher_verify_custom_setting(matcher: Type[Matcher], message: MessageSegment, state):
    key: str = state['key']
    if key in image_custom_settings and message.type != 'image':
        await matcher.finish(f'invalid message type {message.type}, expected image')
    elif key in text_custom_settings and message.type != 'text':
        await matcher.finish(f'invalid message type {message.type}, expected text')
    elif not (key in image_custom_settings or key in text_custom_settings):
        await matcher.finish(f'unknown key {key}')


async def matcher_set_custom_setting(matcher: Type[Matcher], message: MessageSegment, state):
    group_setting: Group = state['group_setting']
    key: str = state['key']
    target: str = state['target']
    await matcher_verify_custom_setting(matcher, message, state)
    if target == '*':
        filename = f'default_{key}'
    else:
        filename = f'{(await group_setting.get_user(target)).user_id}_{key}'
    if key in image_custom_settings:
        filename += '.png'
        filepath = f'{group_setting.database_path}\\{filename}'
        nonebot.logger.debug(f'message = {message}')
        flag = await save_image_to_disk(message.data.get('url'), filepath)
        if not flag:
            await matcher.finish('download image failed')
    else:
        filename += '.txt'
        filepath = f'{group_setting.database_path}\\{filename}'
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(str(message))
    key = f'custom_{key}'
    if target == '*':
        results = await group_setting.modify_users(key, filepath)
        result_message = await make_results_message(key, results)
    else:
        result = await group_setting.modify_user(target, key, filepath)
        result_message = await make_result_message(key, result)
    await matcher.finish(result_message)

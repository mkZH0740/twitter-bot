import aiohttp
import aiofiles

from typing import Type
from nonebot.adapters.cqhttp.message import MessageSegment
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp import GroupMessageEvent

from ..utils import get_group_setting
from ...database import Database, custom_types


async def modify_user_setting(matcher: Type[Matcher], event: GroupMessageEvent, database: Database, value: bool):
    group_setting = await get_group_setting(matcher, database, event.group_id)
    args = str(event.get_message()).strip().split(';')
    match args:
        case[screen_name, key]:
            (_, message) = await group_setting.modify_user_setting(f'receive_{key}', value, screen_name=screen_name)
            await matcher.finish(message)
        case[key]:
            (_, message) = await group_setting.modify_user_setting(f'receive_{key}', value)
            await matcher.finish(message)
        case _:
            await matcher.finish(f'参数个数非法，当前：{len(args)}，需要：1或2')


async def save_image_to_disk(url: str, path: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return False
            async with aiofiles.open(path, 'wb') as f:
                await f.write(await response.read())
            return True

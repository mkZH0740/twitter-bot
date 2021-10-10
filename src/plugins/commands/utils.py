from typing import Type
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.matcher import Matcher

from ..database import Database


async def get_group_setting(matcher: Type[Matcher], database: Database, group_id: int):
    group_setting = await database.get_group_setting(group_id)
    if group_setting is None:
        await matcher.finish(f'群{group_id}未注册')
    return group_setting

from nonebot.plugin import require, on_command
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Bot, GroupMessageEvent

from ..utils import get_group_setting
from ...twitter import StreamHolder
from ...database import Database


twitter_dict = require('twitter')
stream_holder: StreamHolder = twitter_dict.stream_holder
database_dict = require('database')
database: Database = database_dict.database

add_twitter_user_command = on_command('add')
add_twitter_user_command.__doc__ = """add: 在当前群订阅推特用户，eg: #add <screen name>，screen name可以在推特链接中找到，
（eg: https://twitter.com/TAKATOSHI_Gship， 则screen name为 TAKATOSHI_Gship，对应的命令为#add TAKATOSHI_Gship）"""


@add_twitter_user_command.handle()
async def add_twitter_user_handler(bot: Bot, event: GroupMessageEvent, state: T_State):
    screen_name = str(event.get_message()).strip()
    group_setting = await get_group_setting(add_twitter_user_command, database, event.group_id)
    match await stream_holder.client_get_user(screen_name):
        case[True, user]:
            (flag, message) = await group_setting.register_user_setting(user.id, screen_name)
            if flag:
                await stream_holder.run_stream()
            await add_twitter_user_command.finish(message)
        case _:
            await add_twitter_user_command.finish('获取用户失败，请检查screen_name是否正确')


delete_twitter_user_command = on_command('delete')
delete_twitter_user_command.__doc__ = """delete: 在当前群删除订阅的推特用户,eg: #delete <screen name>，screen name可以在推特链接中找到，
（eg: https://twitter.com/TAKATOSHI_Gship， 则screen name为 TAKATOSHI_Gship，对应的命令为#delete TAKATOSHI_Gship）"""


@delete_twitter_user_command.handle()
async def delete_twitter_user_handler(bot: Bot, event: GroupMessageEvent, state: T_State):
    screen_name = str(event.get_message()).strip()
    group_setting = await get_group_setting(add_twitter_user_command, database, event.group_id)
    match await stream_holder.client_get_user(screen_name):
        case[True, user]:
            (flag, message) = await group_setting.unregister_user_setting(user.id, screen_name)
            if flag:
                await stream_holder.run_stream()
            await add_twitter_user_command.finish(message)
        case _:
            await add_twitter_user_command.finish('获取用户失败，请检查screen_name是否正确')

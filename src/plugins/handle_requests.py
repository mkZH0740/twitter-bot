import nonebot

from nonebot.plugin import on_request, on_notice, require
from nonebot.adapters.cqhttp import Bot, FriendRequestEvent, GroupRequestEvent, GroupDecreaseNoticeEvent

from .database import Database
from .twitter import StreamHolder


database_dict = require('database')
database: Database = database_dict.database
twitter_dict = require('twitter')
stream_holder: StreamHolder = twitter_dict.stream_holder


@on_request().handle()
async def friend_request_handler(bot: Bot, event: FriendRequestEvent, state):
    admin_qq: int = nonebot.get_driver().config.admin_qq
    await bot.send_private_msg(user_id=admin_qq, message=f'接受{event.user_id}的好友请求')
    # await bot.set_friend_add_request(flag=event.flag, approve=True)


@on_request().handle()
async def group_request_handler(bot: Bot, event: GroupRequestEvent, state):
    if event.sub_type == 'invite':
        admin_qq: int = nonebot.get_driver().config.admin_qq
        (flag, content) = await database.register_group_setting(group_id=event.group_id)
        await bot.send_private_msg(user_id=admin_qq, message=f'接受{event.group_id}的群邀请，注册结果为{flag}, {content}')
        # await bot.set_group_add_request(flag=event.flag, sub_type='invite', approve=True)


@on_notice().handle()
async def group_unregister_handler(bot: Bot, event: GroupDecreaseNoticeEvent, state):
    if event.self_id == event.user_id:
        admin_qq: int = nonebot.get_driver().config.admin_qq
        (flag, content) = await database.unregister_group_setting(group_id=event.group_id)
        await bot.send_private_msg(user_id=admin_qq, message=f'退出群{event.group_id}，退出结果为{flag}, {content}')
        await stream_holder.run_stream()

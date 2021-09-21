from asyncio import Queue
from typing import Union

import nonebot
from nonebot import export
from nonebot.adapters.cqhttp import Bot
from nonebot.adapters.cqhttp.exception import ActionFailed

from .models import Tweet
from .stream import Stream
from ..database import BotDatabase

bot_database: BotDatabase = nonebot.require('database').bot_database
stream_queue = Queue()


async def consume():
    while True:
        pair: tuple[bool, Union[Tweet, str]] = await stream_queue.get()
        flag, content = pair
        bot: Bot = nonebot.get_bot()
        if flag:
            # content is type Tweet
            groups = await bot_database.get_interested_groups(content.user.id)
            for group in groups:
                message = await content.make_message(group)
                try:
                    await bot.send_group_msg(group_id=group.group_id, message=message)
                except ActionFailed as e:
                    nonebot.logger.warning(
                        f'send to group {group.group_id} failed with retcode = {getattr(e, "retcode")}')
        else:
            # content is type str
            await bot.send_private_msg(user_id=nonebot.get_driver().config.superuser_id, message=content)


async def make_stream():
    config = nonebot.get_driver().config
    twitter_consumer_key = getattr(config, 'twitter_consumer_key')
    twitter_consumer_secret = getattr(config, 'twitter_consumer_secret')
    twitter_access_token = getattr(config, 'twitter_access_token')
    twitter_access_token_secret = getattr(config, 'twitter_access_token_secret')

    twitter_stream = Stream(twitter_consumer_key, twitter_consumer_secret,
                            twitter_access_token, twitter_access_token_secret)
    twitter_stream.stream_queue = stream_queue
    twitter_stream.registered_users = [user.user_id for user in await bot_database.get_all_registered_users()]

    return twitter_stream


twitter_dict = export()
twitter_dict.make_stream = make_stream
twitter_dict.consume = consume

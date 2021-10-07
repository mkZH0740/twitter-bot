import asyncio
from asyncio import Queue, Task
from typing import Union, Optional

import nonebot
from aiohttp.client_exceptions import ClientConnectionError
from tweepy import Client, User, Response
from nonebot.adapters.cqhttp import Bot, ActionFailed

from ..db import BotDatabase
from ..external import ExternalHolder
from .models import Tweet
from .stream import Stream


class StreamHolder:
    stream: Optional[Stream] = None
    client: Optional[Client] = None
    stream_queue: Queue[tuple[bool, Union[str, Tweet]]]
    bot_database: BotDatabase
    external_holder: ExternalHolder
    consume_task: Optional[Task] = None

    def __init__(self, bot_database: BotDatabase, external_holder: ExternalHolder):
        self.bot_database = bot_database
        self.external_holder = external_holder
        config = nonebot.get_driver().config
        self.twitter_consumer_key = getattr(config, 'twitter_consumer_key')
        self.twitter_consumer_secret = getattr(config, 'twitter_consumer_secret')
        self.twitter_access_token = getattr(config, 'twitter_access_token')
        self.twitter_access_token_secret = getattr(config, 'twitter_access_token_secret')
        self.twitter_bearer_token = getattr(config, 'twitter_bearer_token')
        self.stream_queue = Queue()

    async def disconnect_stream(self):
        self.stream.disconnect()

    async def run_stream(self):
        if self.stream is not None:
            await self.disconnect_stream()
        self.stream = Stream(self.twitter_consumer_key, self.twitter_consumer_secret,
                             self.twitter_access_token, self.twitter_access_token_secret)
        self.stream.stream_queue = self.stream_queue
        self.stream.registered_users = [user_setting.user_id for user_setting in await self.bot_database.get_all_users()]
        nonebot.logger.debug(f'running stream with registered users {self.stream.registered_users}')
        self.stream.filter(follow=self.stream.registered_users)

    async def consume_stream(self):
        while True:
            (flag, content) = await self.stream_queue.get()
            try:
                bot: Bot = nonebot.get_bot()
            except ValueError as e:
                nonebot.logger.debug('StreamHolder.consume_stream -> get bot failed')
                continue
            if not flag:
                admin_qq: int = nonebot.get_driver().config.admin_qq
                try:
                    await bot.send_private_msg(user_id=admin_qq, message=content)
                except ActionFailed as e:
                    nonebot.logger.debug(f'StreamHolder.consume_stream -> send private msg failed {getattr(e, "retcode")}')
            else:
                group_settings = await self.bot_database.get_groups_registered_for_user(content.user.id)
                nonebot.logger.debug(f'consuming tweet with groups {group_settings}')
                for group_setting in group_settings:
                    try:
                        message = await content.make_message(group_setting)
                    except ClientConnectionError:
                        await self.external_holder.reboot_server()
                        message = f'服务端未响应，请联系管理员，该推特为{content.tweet_url}'
                        await asyncio.sleep(5)
                    except Exception as e:
                        nonebot.logger.debug(f'StreamHolder.consume_stream ->exception occurred {e}')
                        continue
                    try:
                        await bot.send_group_msg(group_id=group_setting.group_id, message=message)
                    except ActionFailed as e:
                        nonebot.logger.debug(
                            f'StreamHolder.consume_stream -> send to group {group_setting.group_id} failed {getattr(e, "retcode")}'
                        )
                await content.clean_up()

    async def shutdown(self):
        await self.disconnect_stream()
        self.consume_task.cancel()

    async def startup(self):
        await self.run_stream()
        if self.consume_task is not None:
            self.consume_task.cancel()
        self.consume_task = asyncio.create_task(self.consume_stream())

    async def get_user_through_client(self, screen_name: str) -> tuple[bool, Optional[User]]:
        if self.client is None:
            self.client = Client(
                bearer_token=self.twitter_bearer_token,
                consumer_key=self.twitter_consumer_key,
                consumer_secret=self.twitter_consumer_secret,
                access_token=self.twitter_access_token,
                access_token_secret=self.twitter_access_token_secret
            )
        response: Response = self.client.get_user(username=screen_name)
        if isinstance(response.data, User):
            return True, response.data
        else:
            return False, None

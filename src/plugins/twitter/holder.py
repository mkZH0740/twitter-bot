import nonebot
from nonebot.adapters.cqhttp import Bot
from nonebot.adapters.cqhttp import ActionFailed
from typing import Optional, Union
from asyncio import Queue
from asyncio import Task
from tweepy import Client
from tweepy import User

from .stream import Stream
from .models import Tweet
from ..database import BotDatabase


class StreamHolder:
    stream: Optional[Stream] = None
    client: Optional[Client] = None
    queue: Queue[tuple[bool, Union[Tweet, str]]]
    bot_database: BotDatabase
    consume_task: Task = None

    def __init__(self, bot_database: BotDatabase):
        config = nonebot.get_driver().config
        self.twitter_consumer_key = getattr(config, 'twitter_consumer_key')
        self.twitter_consumer_secret = getattr(config, 'twitter_consumer_secret')
        self.twitter_access_token = getattr(config, 'twitter_access_token')
        self.twitter_access_token_secret = getattr(config, 'twitter_access_token_secret')
        self.twitter_bearer_token = getattr(config, 'twitter_bearer_token')
        self.queue = Queue()
        self.bot_database = bot_database

    async def cancel_stream(self):
        self.stream.disconnect()
        self.stream = None

    async def run_stream(self):
        if self.stream is not None:
            await self.cancel_stream()
        self.stream = Stream(self.twitter_consumer_key, self.twitter_consumer_secret,
                             self.twitter_access_token, self.twitter_access_token_secret)
        self.stream.stream_queue = self.queue
        self.stream.registered_users = [user.user_id for user in await self.bot_database.get_all_registered_users()]
        nonebot.logger.debug(f'starting stream with followed user: {self.stream.registered_users}')
        self.stream.filter(follow=self.stream.registered_users)

    async def consume(self):
        while True:
            flag, content = await self.queue.get()
            bot: Bot = nonebot.get_bot()
            if not flag:
                await bot.send_private_msg(user_id=nonebot.get_driver().config.admin_qq, message=content)
                # restart stream, no need to restart this function
                await self.run_stream()
            else:
                groups = await self.bot_database.get_interested_groups(content.user.id)
                nonebot.logger.debug(f'received tweet, interested groups: {groups}, making message for every group')
                for group in groups:
                    message = await content.make_message(group)
                    try:
                        await bot.send_group_msg(group_id=group.group_id, message=message)
                    except ActionFailed as e:
                        nonebot.logger.warning(f'send to group {group.group_id} failed with retcode = {getattr(e, "retcode")}')
                await content.clean_up()

    async def clean_up(self):
        await self.cancel_stream()
        self.consume_task.cancel()

    async def get_user_id_by_screen_name(self, screen_name: str):
        if self.client is None:
            self.client = Client(
                bearer_token=self.twitter_bearer_token,
                consumer_key=self.twitter_consumer_key,
                consumer_secret=self.twitter_consumer_secret,
                access_token=self.twitter_access_token,
                access_token_secret=self.twitter_access_token_secret
            )
        user: Optional[User] = self.client.get_user(username=screen_name)
        if user is None:
            raise RuntimeError(f'unknown user screen_name {screen_name}')
        return user.id

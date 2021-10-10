import asyncio
import nonebot

from asyncio import Queue
from asyncio.tasks import Task
from typing import Literal
from nonebot.adapters.cqhttp import Bot
from tweepy import Response, Client, User

from ..send import send_private_message
from ..database import Database
from ..external import ExternalHolder
from .models import Tweet
from .stream import Stream


class StreamHolder:
    stream: Stream = None
    client: Client = None
    stream_queue: Queue[tuple[Literal[True], Tweet], tuple[Literal[False], str]] = None
    database: Database = None
    external_holder: ExternalHolder = None
    consume_task: Task = None

    def __init__(self, database: Database, external_holder: ExternalHolder) -> None:
        self.database = database
        self.external_holder = external_holder
        config = nonebot.get_driver().config
        self.twitter_consumer_key = getattr(config, 'twitter_consumer_key')
        self.twitter_consumer_secret = getattr(config, 'twitter_consumer_secret')
        self.twitter_access_token = getattr(config, 'twitter_access_token')
        self.twitter_access_token_secret = getattr(config, 'twitter_access_token_secret')
        self.twitter_bearer_token = getattr(config, 'twitter_bearer_token')
        self.stream_queue = Queue()
    
    async def run_stream(self):
        if self.stream is not None:
            self.stream.disconnect()
        stream = Stream(self.twitter_consumer_key, self.twitter_consumer_secret,
                        self.twitter_access_token, self.twitter_access_token_secret)
        stream.stream_queue = self.stream_queue
        stream.registered_users = [user_setting.user_id for user_setting in await self.database.get_all_user_settings()]
        self.stream = stream
        self.stream.filter(follow=self.stream.registered_users)
        nonebot.logger.debug(f'running stream with registered users {self.stream.registered_users}')
    
    async def consume_stream(self):
        admin_qq: int = nonebot.get_driver().admin_qq
        while True:
            content = await self.stream_queue.get()
            match content:
                case (True, tweet):
                    try:
                        bot: Bot = nonebot.get_bot()
                    except ValueError:
                        nonebot.logger.warning(f'consume_stream => get bot failed for tweet {tweet.tweet_url}')
                        continue
                    group_settings = await self.database.get_group_registered_for_user(tweet.user_id)
                    for group_setting in group_settings:
                        await tweet.send_message(bot, group_setting)
                    await tweet.clean_up()
                case (False, err_message):
                    await send_private_message(bot, admin_qq, err_message)
                case _:
                    await send_private_message(bot, admin_qq, f'unknown object {content}')
    
    async def startup(self):
        await self.run_stream()
        self.consume_task = asyncio.create_task(self.consume_stream())
    
    async def shutdown(self):
        if self.stream is not None:
            self.stream.disconnect()
        if self.consume_task is not None:
            self.consume_task.cancel()

    async def client_get_user(self, screen_name: str):
        if self.client is None:
            self.client = Client(
                bearer_token=self.twitter_bearer_token,
                consumer_key=self.twitter_consumer_key,
                consumer_secret=self.twitter_consumer_secret,
                access_token=self.twitter_access_token,
                access_token_secret=self.twitter_access_token_secret
            )
        try:
            response: Response = self.client.get_user(username=screen_name)
            if isinstance(response.data, User):
                return True, response.data
            return False, None
        except Exception:
            return False, None

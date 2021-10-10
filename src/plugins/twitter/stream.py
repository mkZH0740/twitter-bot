import nonebot

from asyncio import Queue
from typing import Union
from tweepy.asynchronous import AsyncStream

from .models import Tweet


class Stream(AsyncStream):
    stream_queue: Queue[tuple[bool, Union[str, Tweet]]]
    registered_users: list[int]

    async def on_status(self, status):
        tweet = Tweet(status)
        if tweet.user.id in self.registered_users:
            nonebot.logger.debug(f'Stream -> received tweet from {tweet.user.screen_name}')
            await self.stream_queue.put((True, tweet))

    async def on_closed(self, resp):
        nonebot.logger.debug('error on_closed')
        await self.stream_queue.put((False, f'closed by twitter with response {resp}'))

    async def on_connection_error(self):
        nonebot.logger.debug('error on_connection_error')
        await self.stream_queue.put((False, f'connection error'))

    async def on_request_error(self, status_code):
        nonebot.logger.debug('error on_request_error')
        await self.stream_queue.put((False, f'request error with status code {status_code}'))

    async def on_warning(self, notice):
        nonebot.logger.debug('error on_warning')
        await self.stream_queue.put((False, f'stall warning received {notice}'))

    async def on_exception(self, exception):
        nonebot.logger.debug(f'error on_exception {exception}')
        await self.stream_queue.put((False, f'exception occurred {exception}'))

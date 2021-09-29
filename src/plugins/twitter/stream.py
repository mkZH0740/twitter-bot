import nonebot
from tweepy.asynchronous import AsyncStream
from asyncio import Queue

from .models import Tweet


class Stream(AsyncStream):

    stream_queue: Queue
    registered_users: list[int]

    async def on_status(self, status):
        tweet = Tweet(status)
        if tweet.user.id not in self.registered_users:
            return
        nonebot.logger.debug(f'received tweet from {tweet.user.screen_name}')
        await self.stream_queue.put(('tweet', tweet))

    async def on_closed(self, resp):
        nonebot.logger.debug('error on_closed')
        await self.stream_queue.put(('error', f'closed by twitter with response {resp}'))

    async def on_connection_error(self):
        nonebot.logger.debug('error on_connection_error')
        await self.stream_queue.put(('error', f'connection error'))

    async def on_request_error(self, status_code):
        nonebot.logger.debug('error on_request_error')
        await self.stream_queue.put(('error', f'request error with status code {status_code}'))

    async def on_warning(self, notice):
        nonebot.logger.debug('error on_warning')
        await self.stream_queue.put(('error', f'stall warning received {notice}'))

    async def on_exception(self, exception):
        nonebot.logger.debug(f'error on_exception {exception}')
        await self.stream_queue.put(('error', f'exception occurred {exception}'))

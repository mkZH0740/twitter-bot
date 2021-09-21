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
        await self.stream_queue.put(('tweet', tweet))


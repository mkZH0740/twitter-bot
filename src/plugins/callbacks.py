import asyncio

import nonebot
from nonebot import require
from twitter import StreamHolder
from database import BotDatabase

database_dict = require('database')
twitter_dict = require('twitter')

bot_database: BotDatabase = database_dict.bot_database
stream_holder: StreamHolder = twitter_dict.stream_holder


@nonebot.get_driver().on_startup
async def startup():
    await bot_database.load()
    asyncio.create_task(stream_holder.run_stream())
    asyncio.create_task(stream_holder.consume())
    nonebot.logger.info(f'full startup completed')

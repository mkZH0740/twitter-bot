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
    await stream_holder.run_stream()
    stream_holder.consume_task = asyncio.create_task(stream_holder.consume())
    nonebot.logger.info(f'full startup completed')


@nonebot.get_driver().on_shutdown
async def shutdown():
    await bot_database.save()
    await stream_holder.clean_up()

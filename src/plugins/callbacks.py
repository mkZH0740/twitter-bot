import asyncio
import nonebot
from nonebot import require
from twitter import StreamHolder
from database import BotDatabase
from nonebot.adapters.cqhttp import Bot

from external import ExternalHolder

database_dict = require('database')
twitter_dict = require('twitter')
external_dict = require('external')

bot_database: BotDatabase = database_dict.bot_database
stream_holder: StreamHolder = twitter_dict.stream_holder
external_holder: ExternalHolder = external_dict.external_holder


@nonebot.get_driver().on_startup
async def startup():
    await bot_database.load()
    await stream_holder.run_stream()
    stream_holder.consume_task = asyncio.create_task(stream_holder.consume())
    await external_holder.run()
    nonebot.logger.info('full startup completed')


@nonebot.get_driver().on_shutdown
async def shutdown():
    nonebot.logger.warning(f'bot shutdown function triggered')
    await bot_database.save()
    await stream_holder.clean_up()
    await external_holder.shutdown()
    nonebot.logger.info('shutdown completed')


@nonebot.get_driver().on_bot_disconnect
async def disconnect(bot: Bot):
    nonebot.logger.warning(f'bot disconnect function triggered')
    await external_holder.reboot_cq_http()

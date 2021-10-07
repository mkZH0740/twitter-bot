import nonebot
from nonebot import require
from twitter import StreamHolder
from db import BotDatabase
from external import ExternalHolder


db_dict = require('db')
twitter_dict = require('twitter')
external_dict = require('external')

bot_database: BotDatabase = db_dict.bot_database
stream_holder: StreamHolder = twitter_dict.stream_holder
external_holder: ExternalHolder = external_dict.external_holder


@nonebot.get_driver().on_startup
async def startup():
    await bot_database.load_group_settings()
    await external_holder.startup()
    nonebot.logger.debug(f'startup completed')


@nonebot.get_driver().on_shutdown
async def shutdown():
    await bot_database.save_group_settings()
    await stream_holder.shutdown()
    await external_holder.shutdown()
    nonebot.logger.debug(f'shutdown completed')


@nonebot.get_driver().on_bot_connect
async def connect(bot):
    await stream_holder.startup()


@nonebot.get_driver().on_bot_disconnect
async def disconnect(bot):
    await external_holder.reboot_cq_http()

import nonebot

from nonebot.plugin import require

from .twitter import StreamHolder
from .external import ExternalHolder
from .database import Database


database_dict = require('database')
database: Database = database_dict.database
twitter_dict = require('twitter')
stream_holder: StreamHolder = twitter_dict.stream_holder
external_dict = require('external')
external_holder: ExternalHolder = external_dict.external_holder


@nonebot.get_driver().on_startup
async def startup():
    await database.load()
    await external_holder.startup()
    nonebot.logger.debug('startup completed')


@nonebot.get_driver().on_shutdown
async def shutdown():
    await database.save()
    await stream_holder.shutdown()
    await external_holder.shutdown()
    nonebot.logger.debug('shutdown completed')


@nonebot.get_driver().on_bot_connect
async def bot_connect(bot):
    await stream_holder.startup()


@nonebot.get_driver().on_bot_disconnect
async def bot_disconnect(bot):
    await external_holder.reboot_cq_http()

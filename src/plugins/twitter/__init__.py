import nonebot
from nonebot import export

from .models import Tweet
from .holder import StreamHolder
from .stream import Stream
from ..db import BotDatabase
from ..external import ExternalHolder

bot_database: BotDatabase = nonebot.require('db').bot_database
external_holder: ExternalHolder = nonebot.require('external').external_holder

stream_holder = StreamHolder(bot_database, external_holder)

twitter_dict = export()
twitter_dict.stream_holder = stream_holder

from asyncio import Queue
from typing import Union

import nonebot
from nonebot import export

from .models import Tweet
from .holder import StreamHolder
from .stream import Stream
from ..database import BotDatabase

bot_database: BotDatabase = nonebot.require('database').bot_database

stream_holder = StreamHolder(bot_database)


twitter_dict = export()
twitter_dict.stream_holder = stream_holder

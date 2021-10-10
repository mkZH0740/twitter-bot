from nonebot.plugin import require, export

from .holder import StreamHolder

from ..database import Database
from ..external import ExternalHolder


database_dict = require('database')
database: Database = database_dict.database
external_dict = require('external')
external_holder: ExternalHolder = external_dict.external_holder

stream_holder = StreamHolder(database, external_holder)

twitter_dict = export()
twitter_dict.stream_holder = stream_holder

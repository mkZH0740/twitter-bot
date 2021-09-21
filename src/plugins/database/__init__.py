from nonebot import export
from .datasource import BotDatabase

database_dict = export()
database_dict.bot_database = BotDatabase()

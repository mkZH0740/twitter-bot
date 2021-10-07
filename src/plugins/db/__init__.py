from nonebot import export

from .datasource import BotDatabase
from .models import GroupSetting, UserSetting

db_dict = export()
db_dict.bot_database = BotDatabase()

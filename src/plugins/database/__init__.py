from nonebot.plugin import export

from .models import UserSetting, GroupSetting, custom_types
from .datasource import Database


database_dict = export()
database_dict.database = Database()

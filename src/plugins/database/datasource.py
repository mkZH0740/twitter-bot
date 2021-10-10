import os
import nonebot

from .models import GroupSetting, UserSetting


class Database:
    database_path: str
    group_settings: dict[int, GroupSetting]

    def __init__(self) -> None:
        self.database_path = nonebot.get_driver().config.database_path
        self.group_settings = dict()

    async def load(self):
        nonebot.logger.debug(f'{self} => load started')
        group_databases = os.listdir(self.database_path)
        for group_database in group_databases:
            if not group_database.isdigit():
                continue
            group_setting = GroupSetting(
                int(group_database), self.database_path)
            await group_setting.load()
            self.group_settings[group_setting.group_id] = group_setting
        nonebot.logger.debug(f'{self} => load completed')

    async def save(self):
        nonebot.logger.debug(f'{self} => save started')
        for group_setting in self.group_settings.values():
            await group_setting.save()
        nonebot.logger.debug(f'{self} => save completed')

    async def get_group_setting(self, group_id: int):
        return self.group_settings.get(group_id)

    async def register_group_setting(self, group_id: int):
        if group_id in self.group_settings:
            return self.__err(f'已存在群{group_id}')
        self.group_settings[group_id] = GroupSetting(
            group_id, self.database_path)
        return self.__ok(f'注册群{group_id}成功')

    async def unregister_group_setting(self, group_id: int):
        if group_id not in self.group_settings:
            return self.__err(f'不存在群{group_id}')
        self.group_settings.pop(group_id)
        return self.__ok(f'删除群{group_id}成功')

    async def get_group_registered_for_user(self, user_id: int):
        return [group_setting for group_setting in self.group_settings.values() if user_id in group_setting.user_settings]

    async def get_all_user_settings(self) -> list[UserSetting]:
        user_settings = list()
        for group_setting in self.group_settings.values():
            user_settings.extend(group_setting.user_settings.values())
        return user_settings

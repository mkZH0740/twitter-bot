import os
import shutil

import nonebot

from aiofiles import os as async_os

from .models import GroupSetting, UserSetting


class BotDatabase:
    database_path: str
    registered_groups: dict[int, GroupSetting]

    def __init__(self):
        self.database_path = nonebot.get_driver().config.database_path
        self.registered_groups = dict()

    def __ok_result(self, msg: str):
        return True, f'BotDatabase -> {msg}'

    def __err_result(self, msg: str):
        return False, f'BotDatabase -> {msg}'

    async def load_group_settings(self):
        nonebot.logger.debug(f'BotDatabase -> load started')
        group_databases = os.listdir(self.database_path)
        for group_database in group_databases:
            if not group_database.isdigit():
                continue
            group_setting = GroupSetting(int(group_database), self.database_path)
            await group_setting.load_group_setting()
            self.registered_groups[group_setting.group_id] = group_setting
        nonebot.logger.debug(f'BotDatabase -> load completed')

    async def save_group_settings(self):
        nonebot.logger.debug(f'BotDatabase -> save started')
        for group_setting in self.registered_groups.values():
            await group_setting.save_group_setting()
        nonebot.logger.debug(f'BotDatabase -> save completed')

    async def get_group_setting(self, group_id: int):
        return self.registered_groups.get(group_id)

    async def register_group_setting(self, group_id: int):
        if group_id in self.registered_groups:
            return self.__err_result(f'群{group_id}已注册')
        group_setting = GroupSetting(group_id, self.database_path)
        await async_os.mkdir(group_setting.group_database_path)
        self.registered_groups[group_id] = group_setting
        return self.__ok_result(f'群{group_id}注册完成')

    async def unregister_group_setting(self, group_id: int):
        if group_id not in self.registered_groups:
            return self.__err_result(f'群{group_id}未注册')
        group_setting = self.registered_groups.pop(group_id)
        shutil.rmtree(group_setting.group_database_path)
        return self.__ok_result(f'群{group_id}注册已取消')

    async def get_groups_registered_for_user(self, user_id: int):
        return [group_setting for group_setting in self.registered_groups.values()
                if user_id in group_setting.registered_users]

    async def get_all_users(self):
        result = []
        for group_setting in self.registered_groups.values():
            result.extend(group_setting.registered_users.values())
        return list(set(result))

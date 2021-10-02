import json
import os
import shutil

import aiofiles
import nonebot
from aiofiles import os as async_os

from .models import UserSetting, GroupSetting


class BotDatabase:
    database_path: str

    registered_groups: dict[int, GroupSetting]

    def __init__(self):
        self.database_path = nonebot.get_driver().config.database_path
        self.registered_groups = dict()

    def __make_err_msg(self, msg: str):
        return False, f'{type(self)} -> {msg}'

    def __make_success_msg(self, msg: str):
        return True, f'{type(self)} -> {msg}'

    async def load(self):
        group_database_paths = os.listdir(self.database_path)
        for group_database_path in group_database_paths:
            if not group_database_path.isdigit():
                continue
            group = GroupSetting(int(group_database_path), f'{self.database_path}\\{group_database_path}')
            await group.load()
            self.registered_groups[group.group_id] = group

    async def save(self):
        for group in self.registered_groups.values():
            await group.save()

    async def get_group(self, group_id: int):
        return self.registered_groups.get(group_id)

    async def register_group(self, group_id: int):
        if group_id in self.registered_groups:
            return self.__make_err_msg(f'group {group_id} already exists')
        group = GroupSetting(group_id, f'{self.database_path}\\{group_id}')
        await async_os.mkdir(group.database_path)

        async with aiofiles.open(f'{group.database_path}\\user.json', 'w', encoding='utf-8') as f:
            await f.write(json.dumps({}, ensure_ascii=False, indent=4))
        f = await aiofiles.open(f'{group.database_path}\\histories.txt', 'w', encoding='utf-8')
        await f.close()

        self.registered_groups[group_id] = group
        return self.__make_success_msg(f'group {group_id} registered')

    async def delete_group(self, group_id: int):
        if group_id not in self.registered_groups:
            return self.__make_err_msg(f'unknown group {group_id}')
        group = self.registered_groups.pop(group_id)
        shutil.rmtree(group.database_path)
        return self.__make_success_msg(f'group {group_id} deleted')

    async def get_interested_groups(self, user_id: int):
        return [group for group in self.registered_groups.values() if user_id in group.registered_users]

    async def get_all_registered_users(self):
        result = []
        for group in self.registered_groups.values():
            result.extend(group.registered_users.values())
        return list(set(result))

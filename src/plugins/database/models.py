import os
import json
import aiofiles
import nonebot

from typing import Any, Optional
from aiofiles.os import mkdir


max_history_amount = 1000
custom_types = {
    'tag': 'image',
    'background': 'image',
    'css': 'text'
}


class UserSetting:
    user_id: int
    screen_name: str

    # user tweet receive settings
    receive_tweet: bool = True
    receive_retweet: bool = True
    receive_comment: bool = True

    # user tweet component settings
    receive_text: bool = True
    receive_screenshot: bool = True
    receive_translation: bool = True
    receive_content: bool = True

    # user tweet receive message setting
    receive_collapsed_message: bool = True

    # user custom settins
    custom_tag: Optional[str] = None
    custom_background: Optional[str] = None
    custom_css: Optional[str] = None

    def __init__(self, user_id: int = -1, screen_name: str = '') -> None:
        self.user_id = user_id
        self.screen_name = screen_name

    async def modify(self, key: str, value: bool):
        if not hasattr(self, key) or not key.startswith('receive'):
            return self.__err(f'不支持设置{key}')
        if not isinstance(value, bool):
            return self.__err(f'非法值类型{type(value)}，需要bool')
        curr_value: bool = getattr(self, key)
        setattr(self, key, value)
        return self.__ok(f'设置完成，{key}的值由{curr_value}设置为{value}')

    async def to_json(self):
        return vars(self)

    @staticmethod
    async def from_json(json_content: dict[str, Any]):
        if 'user_id' not in json_content or 'screen_name' not in json_content:
            return None
        user_setting = UserSetting()
        for key, value in json_content.items():
            setattr(user_setting, key, value)
        return user_setting

    def __ok(self, message: str):
        return True, f'{self} => {message}'

    def __err(self, message: str):
        return False, f'{self} => {message}'

    def __str__(self) -> str:
        return f'[{type(self).__name__} {self.screen_name}]'

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, type(self)) and o.user_id == self.user_id:
            return True
        return False

    def __hash__(self) -> int:
        return self.user_id


class GroupSetting:
    group_id: int
    group_database_path: str

    user_settings: dict[int, UserSetting]
    history: list[str]

    def __init__(self, group_id: int, database_path: str) -> None:
        self.group_id = group_id
        self.group_database_path = f'{database_path}\\{group_id}'
        self.user_settings = dict()
        self.history = list()

    async def get_user_setting(self, user_id: int = None, screen_name: str = None):
        if user_id is None:
            for user_setting in self.user_settings.values():
                if user_setting.screen_name == screen_name:
                    return user_setting
            return None
        else:
            return self.user_settings.get(user_id)

    async def register_user_setting(self, user_id: int, screen_name: str):
        if user_id in self.user_settings:
            return self.__err(f'已存在用户{screen_name}')
        self.user_settings[user_id] = UserSetting(user_id, screen_name)
        return self.__ok(f'注册用户{screen_name}成功')

    async def unregister_user_setting(self, user_id: int, screen_name: str):
        if user_id not in self.user_settings:
            return self.__err(f'不存在用户{screen_name}')
        self.user_settings.pop(user_id)
        return self.__ok(f'删除用户{screen_name}成功')

    async def modify_user_setting(self, key: str, value: bool, user_id: int = None, screen_name: str = None):
        result_message = ''
        if user_id is None and screen_name is None:
            for user_setting in self.user_settings.values():
                (_, message) = await user_setting.modify(key, value)
                result_message += message + '\n'
        else:
            user_setting = await self.get_user_setting(user_id, screen_name)
            if user_setting is None:
                result_message = f'不存在用户{screen_name}'
            else:
                (_, message) = await user_setting.modify(key, value)
                result_message = message
        return self.__ok(result_message.strip())

    async def add_history(self, url: str):
        self.history.append(url)
        if len(self.history) >= max_history_amount:
            self.history = self.history[max_history_amount / 2:]
        return len(self.history)

    async def get_history(self, index: int):
        if index < 1 or index > len(self.history):
            return self.__err(f'非法编号，编号应在1和{len(self.history)}之间')
        return True, self.history[index]

    async def load(self):
        user_setting_path = f'{self.group_database_path}\\user.json'
        if os.path.exists(user_setting_path):
            async with aiofiles.open(user_setting_path, 'r', encoding='utf-8') as f:
                json_content: dict = json.loads(await f.read())
                for user_json_content in json_content.values():
                    user_setting = await UserSetting.from_json(user_json_content)
                    if user_setting is not None:
                        self.user_settings[user_setting.user_id] = user_setting
        history_path = f'{self.group_database_path}\\history.txt'
        if os.path.exists(history_path):
            async with aiofiles.open(history_path, 'r', encoding='utf-8') as f:
                history_lines = await f.readlines()
                self.history = [line.strip()
                                for line in history_lines if line != '\n']
        nonebot.logger.debug(f'{self} => load completed')

    async def save(self):
        user_setting_path = f'{self.group_database_path}\\user.json'
        if not os.path.exists(self.group_database_path):
            await mkdir(self.group_database_path)
        user_setting_content = {user_id: await user_setting.to_json() for user_id, user_setting in self.user_settings.items()}
        async with aiofiles.open(user_setting_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(user_setting_content, ensure_ascii=False, indent=4))
        history_path = f'{self.group_database_path}\\history.txt'
        async with aiofiles.open(history_path, 'w', encoding='utf-8') as f:
            await f.writelines([f'{line}\n' for line in self.history])
        nonebot.logger.debug(f'{self} => save completed')

    def __str__(self) -> str:
        return f'[{type(self).__name__} {self.group_id}]'

    def __repr__(self) -> str:
        return str(self)

    def __ok(self, message: str):
        return True, f'{self} => {message}'

    def __err(self, message: str):
        return False, f'{self} => {message}'

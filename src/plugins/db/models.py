import json
import os.path

import nonebot
import aiofiles

from typing import Optional, Any, Union

max_history_amount = 1000
custom_types = {
    'tag': 'image',
    'background': 'image',
    'css': 'text'
}


class UserSetting:
    user_id: int
    screen_name: str

    receive_tweet: bool = True
    receive_retweet: bool = True
    receive_comment: bool = True

    receive_text: bool = True
    receive_translation: bool = True
    receive_screenshot: bool = True
    receive_content: bool = True

    custom_tag: Optional[str] = None
    custom_css: Optional[str] = None
    custom_background: Optional[str] = None

    def __init__(self, user_id: int, screen_name: str):
        self.user_id = user_id
        self.screen_name = screen_name

    def __ok_result(self, msg: str):
        return True, f'{self.screen_name} -> {msg}'

    def __err_result(self, msg: str):
        return False, f'{self.screen_name} -> {msg}'

    async def switch(self, key: str, value: bool):
        if not key.startswith('receive'):
            return self.__err_result(f'不支持设置{key}')
        curr_value: bool = getattr(self, key)
        setattr(self, key, value)
        return self.__ok_result(f'设置完成，{key}由{curr_value}更新为{value}')

    async def to_json_value(self):
        return vars(self)

    @staticmethod
    async def from_json_value(json_value: dict[str, Any]):
        user_id: Optional[int] = json_value.pop('user_id', None)
        screen_name: Optional[str] = json_value.pop('screen_name', None)
        if user_id is None or screen_name is None:
            nonebot.logger.warning('broken group setting, skipping')
            return None
        user_setting = UserSetting(user_id, screen_name)
        for k, v in json_value.items():
            setattr(user_setting, k, v)
        return user_setting

    def __eq__(self, other):
        if isinstance(other, type(self)) and other.user_id == self.user_id:
            return True
        return False

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.user_id)


class GroupSetting:
    group_id: int
    group_database_path: str

    registered_users: dict[int, UserSetting]
    histories: list[str]

    def __init__(self, group_id: int, database_path: str):
        self.group_id = group_id
        self.group_database_path = f'{database_path}\\{group_id}'
        self.registered_users = dict()
        self.histories = list()

    def __ok_result(self, msg: str):
        return True, f'{self.group_id} -> {msg}'

    def __err_result(self, msg: str):
        return False, f'{self.group_id} -> {msg}'

    async def get_user_setting(self, user_id: Optional[int] = None, screen_name: Optional[str] = None) \
            -> tuple[bool, Union[Optional[UserSetting], str]]:
        if user_id is not None:
            user_setting = self.registered_users.get(user_id)
            return (user_setting is not None), user_setting
        elif screen_name is not None:
            user_setting = None
            for registered_setting in self.registered_users.values():
                if registered_setting.screen_name == screen_name:
                    user_setting = registered_setting
                    break
            return (user_setting is not None), user_setting
        else:
            return self.__err_result(f'内部错误，get_user参数不能同时为None')

    async def switch_user_setting(self, key: str, value: Any, user_id: Optional[int] = None,
                                  screen_name: Optional[str] = None):
        (flag, content) = await self.get_user_setting(user_id, screen_name)
        if flag:
            return await content.switch(key, value)
        elif content is None:
            return self.__err_result(f'未注册用户')
        else:
            return self.__err_result(content)

    async def switch_all_user_setting(self, key: str, value: Any):
        results: list[tuple[str, bool, str]] = []
        for user in self.registered_users.values():
            (flag, content) = await user.switch(key, value)
            results.append((user.screen_name, flag, content))
        return results

    async def register_user(self, user_id: int, screen_name: str):
        if user_id in self.registered_users:
            return self.__err_result(f'该用户已注册')
        self.registered_users[user_id] = UserSetting(user_id, screen_name)
        return self.__ok_result(f'用户{screen_name}注册完毕')

    async def unregister_user(self, user_id: int, screen_name: str):
        if user_id not in self.registered_users:
            return self.__err_result(f'该用户未注册')
        self.registered_users.pop(user_id)
        return self.__ok_result(f'用户{screen_name}注册已取消')

    async def add_history(self, history: str):
        self.histories.append(history)
        if len(self.histories) >= max_history_amount:
            self.histories = self.histories[max_history_amount / 2:]
        return len(self.histories)

    async def get_history(self, history_index: int):
        if history_index < 1 or history_index > len(self.histories):
            return self.__err_result(f'不合法的编号{history_index}，编号应在1与{len(self.histories)}之间')
        return True, self.histories[history_index]

    async def save_group_setting(self):
        user_setting_path = f'{self.group_database_path}\\user.json'
        async with aiofiles.open(user_setting_path, 'w', encoding='utf-8') as f:
            content = {user.user_id: await user.to_json_value() for user in self.registered_users.values()}
            await f.write(json.dumps(content, ensure_ascii=False, indent=4))
        history_path = f'{self.group_database_path}\\history.txt'
        async with aiofiles.open(history_path, 'a', encoding='utf-8') as f:
            await f.writelines([f'{line}\n' for line in self.histories])
        nonebot.logger.debug(f'{self} -> save completed')

    async def load_group_setting(self):
        user_setting_path = f'{self.group_database_path}\\user.json'
        if os.path.exists(user_setting_path):
            async with aiofiles.open(user_setting_path, 'r', encoding='utf-8') as f:
                file_content = await f.read()
                json_content: dict[str, dict[str, Any]] = json.loads(file_content)
                for user_json_value in json_content.values():
                    user_setting = await UserSetting.from_json_value(user_json_value)
                    if user_setting is not None:
                        self.registered_users[user_setting.user_id] = user_setting
        history_path = f'{self.group_database_path}\\history.txt'
        if os.path.exists(history_path):
            async with aiofiles.open(history_path, 'r', encoding='utf-8') as f:
                lines = await f.readlines()
                self.histories.extend([line.strip() for line in lines if line != '\n'])
        nonebot.logger.debug(f'{self} -> load completed')

    def __str__(self):
        return f'[GroupSetting {self.group_id}]'

    def __repr__(self):
        return f'[GroupSetting {self.group_id}]'

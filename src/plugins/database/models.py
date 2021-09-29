import json
import os.path
from typing import Optional, Any

import aiofiles
import nonebot


history_list_max_count = 1000
image_custom_settings = ('tag', 'background')
text_custom_settings = ('css',)


class User:
    user_id: int
    screen_name: str

    receive_tweet: bool = True
    receive_retweet: bool = True
    receive_comment: bool = True

    require_text: bool = True
    require_translation: bool = True
    require_screenshot: bool = True
    require_content: bool = True

    custom_tag: Optional[str] = None
    custom_css: Optional[str] = None
    custom_background: Optional[str] = None

    def __init__(self, user_id: int, screen_name: str):
        self.user_id = user_id
        self.screen_name = screen_name

    def __make_err_msg(self, msg: str):
        return False, f'{self.screen_name} -> {msg}'

    def __make_success_msg(self, msg: str):
        return True, f'{self.screen_name} -> {msg}'

    async def modify(self, key: str, value):
        if not hasattr(self, key):
            return self.__make_err_msg(f'unknown key {key}')
        if key == 'user_id' or key == 'screen_name':
            return self.__make_err_msg(f'invalid key {key}')
        curr_value = getattr(self, key)
        if not (key.startswith('custom') or isinstance(value, type(curr_value))):
            return self.__make_err_msg(f'inconsistent type current = {type(curr_value)}, new = {type(value)}')
        if value == curr_value:
            return self.__make_err_msg(f'setting same value {value}')
        setattr(self, key, value)
        return self.__make_success_msg(f'set value completed, new value {value}')

    async def to_json_content(self):
        return vars(self)

    @staticmethod
    async def from_json_content(json_content: dict[str, Any]):
        user_id = json_content.get('user_id')
        screen_name = json_content.get('screen_name')
        if user_id is None or screen_name is None:
            return None
        user = User(user_id, screen_name)
        for k, v in json_content.items():
            setattr(user, k, v)
        return user

    def __eq__(self, other):
        if isinstance(other, type(self)) and other.user_id == self.user_id:
            return True
        return False

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.user_id)


class Group:
    group_id: int
    database_path: str

    registered_users: dict[int, User]
    histories: list[str]

    def __init__(self, group_id: int, database_path: str):
        self.group_id = group_id
        self.database_path = database_path
        self.registered_users = dict()
        self.histories = list()

    def __make_err_msg(self, msg: str):
        return False, f'{self.group_id} -> {msg}'

    def __make_success_msg(self, msg: str):
        return True, f'{self.group_id} -> {msg}'

    async def get_user(self, screen_name: str):
        for user in self.registered_users.values():
            if user.screen_name == screen_name:
                return user
        return None

    async def modify_user(self, screen_name: str, key: str, value):
        user = await self.get_user(screen_name)
        if user is not None:
            return await user.modify(key, value)
        return self.__make_err_msg(f'unknown user {screen_name}')

    async def modify_users(self, key: str, value):
        return {user.screen_name: await user.modify(key, value) for user in self.registered_users.values()}

    async def add_user(self, user_id: int, screen_name: str):
        if user_id in self.registered_users:
            return self.__make_err_msg(f'user {screen_name} already exists')
        self.registered_users[user_id] = User(user_id, screen_name)
        return self.__make_success_msg(f'add user {screen_name} completed')

    async def delete_user(self, screen_name: str):
        for user in self.registered_users.values():
            if user.screen_name == screen_name:
                self.registered_users.pop(user.user_id)
                return self.__make_success_msg(f'delete user {screen_name} completed')
        return self.__make_err_msg(f'unknown user {screen_name}')

    async def add_history(self, history: str):
        self.histories.append(history)
        if len(self.histories) == history_list_max_count:
            self.histories = self.histories[history_list_max_count / 2:]
        return len(self.histories)

    async def get_history(self, index: int):
        if index < 1 or index > len(self.histories):
            return self.__make_err_msg(f'invalid index {index}, current last history index {len(self.histories)}')
        return True, self.histories[index - 1]

    async def save(self):
        user_setting_file_path = f'{self.database_path}\\user.json'
        async with aiofiles.open(user_setting_file_path, 'w', encoding='utf-8') as f:
            content = {user.user_id: await user.to_json_content() for user in self.registered_users.values()}
            await f.write(json.dumps(content, ensure_ascii=False, indent=4))
        histories_file_path = f'{self.database_path}\\histories.txt'
        async with aiofiles.open(histories_file_path, 'w', encoding='utf-8') as f:
            await f.writelines([f'{line}\n' for line in self.histories])

    async def load(self):
        user_setting_file_path = f'{self.database_path}\\user.json'
        histories_file_path = f'{self.database_path}\\histories.txt'
        if os.path.exists(user_setting_file_path):
            async with aiofiles.open(user_setting_file_path, 'r', encoding='utf-8') as f:
                user_content: dict[str, dict[str, Any]] = json.loads(await f.read())
                for json_content in user_content.values():
                    user = await User.from_json_content(json_content)
                    if user is None:
                        continue
                    self.registered_users[user.user_id] = user
        if os.path.exists(histories_file_path):
            async with aiofiles.open(histories_file_path, 'r', encoding='utf-8') as f:
                history_content = await f.readlines()
                if len(history_content) == 0:
                    self.histories = []
                else:
                    history_content.pop()
                    self.histories = [line.strip() for line in history_content]
        nonebot.logger.info(f'group {self.group_id} loaded')

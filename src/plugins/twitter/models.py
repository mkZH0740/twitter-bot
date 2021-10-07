import os.path
from typing import Optional

import nonebot
from nonebot.adapters.cqhttp import MessageSegment
from aiofiles import os as async_os

from .utils import get_screenshot_and_text, get_translation
from ..db import GroupSetting


class TweetUser:
    id: int
    screen_name: str

    def __init__(self, status):
        user = getattr(status, 'author')
        self.id = getattr(user, 'id')
        self.screen_name = getattr(user, 'screen_name')


class TweetEntities:
    has_entities: bool
    media: list[dict]

    def __init__(self, status):
        if hasattr(status, 'extended_entities'):
            entities: dict = getattr(status, 'extended_entities')
            self.media = entities.get('media')
            self.has_entities = True
        else:
            self.media = []
            self.has_entities = False

    async def get_images(self, max_image_count: int = 4):
        results: list[Optional[str]] = []
        for i in range(min(max_image_count, len(self.media))):
            results.append(self.media[i].get('media_url_https'))
        return results


class Tweet:
    tweet_id: int
    tweet_url: str
    tweet_type: str
    user: TweetUser
    entities: TweetEntities

    def __init__(self, status):
        self.status = status
        self.tweet_id = getattr(status, 'id')
        self.user = TweetUser(status)
        self.tweet_url = f'https://twitter.com/{self.user.screen_name}/status/{self.tweet_id}'
        self.entities = TweetEntities(status)
        self.tweet_type = 'tweet'
        if hasattr(status, 'retweeted_status'):
            self.tweet_type = 'retweet'
        elif getattr(status, 'in_reply_to_status_id') is not None:
            self.tweet_type = 'comment'
        self.loaded_content: dict[str, str] = {}

    async def load_text_and_screenshot(self):
        if 'text' not in self.loaded_content:
            result = await get_screenshot_and_text(self.tweet_url)
            result_type = result.get('type')
            if result_type == 'ok':
                screenshot_path = result.get('screenshot_path')
                self.loaded_content['screenshot_path'] = screenshot_path
                self.loaded_content['screenshot_message'] = str(MessageSegment.image(file=f'file:///{screenshot_path}'))
                self.loaded_content['text'] = result.get('text')
            else:
                self.loaded_content['text'] = result.get('message')

    async def load_translation(self):
        if 'translation' not in self.loaded_content:
            self.loaded_content['translation'] = await get_translation(self.loaded_content['text'])

    async def load_content_message(self):
        if 'content_message' not in self.loaded_content:
            content_urls = await self.entities.get_images()
            content_message = ''
            for content_url in content_urls:
                content_message += str(MessageSegment.image(file=content_url))
            self.loaded_content['content_message'] = content_message

    async def make_message(self, group_setting: GroupSetting):
        nonebot.logger.debug(f'making message for group {group_setting.group_id}')
        await self.load_text_and_screenshot()
        if self.loaded_content.get('screenshot_path') is None:
            return self.loaded_content.get('text')
        (flag, content) = await group_setting.get_user_setting(user_id=self.user.id)
        if content is None:
            return f'未注册用户{self.user.screen_name}'
        elif isinstance(content, str):
            return content
        result_message = ''
        nonebot.logger.debug(f'group registered user setting {await content.to_json_value()}')
        if getattr(content, 'receive_screenshot'):
            result_message += self.loaded_content.get('screenshot_message')
        if getattr(content, 'receive_text'):
            result_message += '\n原文：' + self.loaded_content.get('text')
        if getattr(content, 'receive_translation'):
            await self.load_translation()
            result_message += '\n翻译：' + self.loaded_content.get('translation')
        if getattr(content, 'receive_content'):
            await self.load_content_message()
            content_message = self.loaded_content.get('content_message')
            if content_message != '':
                result_message += '\n附件：' + content_message
        group_history_index = await group_setting.add_history(self.tweet_url)
        result_message += f'\n编号：{group_history_index}'
        nonebot.logger.debug(f'making message for group {group_setting.group_id} completed')
        return result_message

    async def clean_up(self):
        screenshot_path = self.loaded_content.get('screenshot_path')
        if screenshot_path is not None and os.path.exists(screenshot_path):
            await async_os.remove(screenshot_path)
        nonebot.logger.debug(f'tweet {self.tweet_url} cleaned up')

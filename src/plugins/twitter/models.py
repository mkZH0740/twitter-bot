import hashlib
import os.path
import random
import urllib.parse
from typing import Optional
from nonebot.adapters.cqhttp import MessageSegment
from aiofiles import os as async_os

import aiohttp
import nonebot

from ..database.models import GroupSetting


class TweetUser:
    id: int
    screen_name: str

    def __init__(self, status):
        user = getattr(status, 'author')
        self.id = getattr(user, 'id')
        self.screen_name = getattr(user, 'screen_name')


class TweetEntities:
    has_entities: bool = False
    media: list[dict]

    def __init__(self, status):
        if hasattr(status, 'extended_entities'):
            entities: dict = getattr(status, 'extended_entities')
            self.media = entities.get('media')
            self.has_entities = True
        else:
            self.media = []

    async def get_images(self, max_image_count: int = 4):
        results: list[Optional[str]] = []
        for i in range(min(max_image_count, len(self.media))):
            results.append(self.media[i].get('media_url_https'))
        return results


class Tweet:
    id: int
    url: str
    tweet_type: str
    user: TweetUser
    entities: TweetEntities

    raw_text: Optional[str] = None
    text_message: Optional[str] = ''
    raw_translation: Optional[str] = None
    translation_message: Optional[str] = ''
    raw_screenshot: Optional[str] = None
    screenshot_message: Optional[str] = ''
    content_message: Optional[str] = ''

    def __init__(self, status):
        self.status = status
        self.id = getattr(status, 'id')
        self.user = TweetUser(status)
        self.url = f'https://twitter.com/{self.user.screen_name}/status/{self.id}'
        self.entities = TweetEntities(status)
        self.tweet_type = 'tweet'
        if hasattr(status, 'retweeted_status'):
            self.tweet_type = 'retweet'
        elif getattr(status, 'in_reply_to_status_id') is not None:
            self.tweet_type = 'comment'

    async def load_text_and_screenshot_message(self):
        if self.raw_screenshot is None:
            async with aiohttp.ClientSession() as session:
                server_url = nonebot.get_driver().config.server_url
                server_path = nonebot.get_driver().config.server_path
                async with session.get(f'{server_url}/screenshot', json={'url': self.url}) as response:
                    if response.status != 200:
                        self.text_message = str(MessageSegment.text('unknown error occurred on server side, please '
                                                                    'contact administrator'))
                    else:
                        result: dict[str, str] = await response.json()
                        if result.get('type') == 'ok':
                            self.raw_screenshot = f'{server_path}\\{result.get("screenshotPath")}'
                            self.screenshot_message = str(MessageSegment.image(file=f'file:///{self.raw_screenshot}'))
                            self.raw_text = result.get('text')
                            self.text_message = str(MessageSegment.text(result.get('text')))
                        elif result.get('type') == 'err':
                            self.text_message = str(MessageSegment.text(result.get('message')))
                        else:
                            self.text_message = str(MessageSegment.text('unknown error occurred on server side, please '
                                                                        'contact administrator'))

    async def load_translation_message(self):
        if self.raw_translation is None and self.raw_text != '':
            async with aiohttp.ClientSession() as session:
                translate_api_url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
                baidu_appid = nonebot.get_driver().config.baidu_appid
                baidu_secret = nonebot.get_driver().config.baidu_secret
                salt = random.randint(32768, 65536)
                sign = f'{baidu_appid}{self.raw_text}{salt}{baidu_secret}'.encode('utf-8')
                md5_module = hashlib.md5()
                md5_module.update(sign)
                sign = md5_module.hexdigest()
                request_url = f'{translate_api_url}?q={urllib.parse.quote(self.raw_text)}&from=auto&to=zh&appid={baidu_appid}&salt={salt}&sign={sign}'
                async with session.get(request_url) as response:
                    if response.status != 200:
                        self.translation_message = str(
                            MessageSegment.text(f'translation request failed with status {response.status}'))
                        return
                    result: dict = await response.json(encoding='utf-8')
                    if 'error_code' in result:
                        self.translation_message = str(
                            MessageSegment.text(f'translation failed with error code {result["error_code"]}'))
                    else:
                        translated_text = ''
                        translated_results: list[dict[str, str]] = result.get('trans_result')
                        for translated_result in translated_results:
                            translated_text += translated_result['dst'] + '\n'
                        self.raw_translation = translated_text.strip()
                        self.translation_message = str(MessageSegment.text(self.raw_translation))

    async def load_content_message(self):
        if self.content_message is None:
            content_urls = await self.entities.get_images()
            for content_url in content_urls:
                self.content_message += str(MessageSegment.image(file=content_url))

    async def make_message(self, group: GroupSetting) -> str:
        await self.load_text_and_screenshot_message()
        if self.screenshot_message == '':
            return f'{self.text_message}'
        curr_user_setting = await group.get_user(self.user.screen_name)
        result_message = ''
        if curr_user_setting.require_screenshot:
            result_message += self.screenshot_message
        if curr_user_setting.require_text:
            result_message += f'\n原文：{self.text_message}'
        if curr_user_setting.require_translation:
            await self.load_translation_message()
            result_message += f'\n翻译：{self.translation_message}'
        if curr_user_setting.require_content and self.entities.has_entities:
            await self.load_content_message()
            result_message += f'\n附件：{self.content_message}'
        curr_group_history_index = await group.add_history(self.url)
        result_message += f'\n编号：{curr_group_history_index}'
        return result_message

    async def clean_up(self):
        if os.path.exists(self.raw_screenshot):
            await async_os.remove(self.raw_screenshot)

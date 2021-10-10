import os
import nonebot

from aiofiles.os import remove
from nonebot.adapters.cqhttp import Bot, MessageSegment
from tweepy import user

from .utils import get_screenshot_and_text, get_translation, make_forward_message_node
from ..database import GroupSetting, UserSetting
from ..send import send_forward_message, send_group_message


class Tweet:
    tweet_id: int
    tweet_url: str
    tweet_type: str
    user_id: int
    user_screen_name: str
    entities: dict
    loaded_content: dict

    def __init__(self, status) -> None:
        self.status = status
        self.tweet_id = getattr(status, 'id')
        self.user = getattr(status, 'author')
        self.user_id = getattr(self.user, 'id')
        self.user_screen_name = getattr(self.user, 'screen_name')
        self.tweet_url = f'https://twitter.com/{self.user_screen_name}/status/{self.tweet_id}'
        self.tweet_type = 'tweet'
        if hasattr(status, 'retweeted_status'):
            self.tweet_type = 'retweet'
        elif getattr(status, 'in_reply_to_status_id') is not None:
            self.tweet_type = 'comment'
        self.entities = getattr(status, 'extended_entities', dict())
        self.loaded_content = dict()

    async def load_screenshot_and_text(self):
        if 'text' not in self.loaded_content:
            await get_screenshot_and_text(self.tweet_url, self.loaded_content)

    async def load_translation(self):
        if 'translation' not in self.loaded_content:
            await get_translation(self.loaded_content['text'], self.loaded_content)

    async def load_content(self):
        if 'content' not in self.loaded_content:
            medias: list[dict] = self.entities.get('media', list())
            media_urls = list()
            for i in range(min(4, len(medias))):
                media_urls.append(medias[i].get('media_url_https'))
            if len(media_urls) != 0:
                self.loaded_content['content'] = media_urls
            else:
                self.loaded_content['content'] = list()

    async def make_normal_message(self, group_setting: GroupSetting, user_setting: UserSetting):
        message = ''
        if user_setting.receive_screenshot and 'screenshot_path' in self.loaded_content:
            screenshot_path = self.loaded_content['screenshot_path']
            screenshot_segment = MessageSegment.image(
                file=f'file:///{screenshot_path}')
            message += str(screenshot_segment)
        if user_setting.receive_text and 'text' in self.loaded_content:
            text = self.loaded_content['text']
            text_segment = MessageSegment.text(text=text)
            message += '\n原文：' + str(text_segment)
        if user_setting.receive_translation:
            await self.load_translation()
            translation = self.loaded_content['translation']
            translation_segment = MessageSegment.text(text=translation)
            message += '\n翻译：' + str(translation_segment)
        if user_setting.receive_content:
            await self.load_content()
            media_urls: list[str] = self.loaded_content['content']
            if len(media_urls) != 0:
                message += '\n附件：'
                for media_url in media_urls:
                    if media_url is not None:
                        message += str(MessageSegment.image(file=media_url))
        history_index = await group_setting.add_history(self.tweet_url)
        message += f'\n编号：{history_index}'
        return message

    async def make_forward_message(self, bot: Bot, group_setting: GroupSetting, user_setting: UserSetting):
        message = list()
        if user_setting.receive_screenshot and 'screenshot_path' in self.loaded_content:
            screenshot_path = self.loaded_content['screenshot_path']
            screenshot_segment = MessageSegment.image(
                file=f'file:///{screenshot_path}')
            screenshot_node = await make_forward_message_node('截图', bot.self_id, screenshot_segment)
            message.append(screenshot_node)
        if user_setting.receive_text and 'text' in self.loaded_content:
            text = self.loaded_content['text']
            text_segment = MessageSegment.text(text=text)
            text_node = await make_forward_message_node('原文', bot.self_id, text_segment)
            message.append(text_node)
        if user_setting.receive_translation:
            await self.load_translation()
            translation = self.loaded_content['translation']
            translation_segment = MessageSegment.text(text=translation)
            translation_node = await make_forward_message_node('翻译', bot.self_id, translation_segment)
            message.append(translation_node)
        if user_setting.receive_content:
            await self.load_content()
            media_urls: list[str] = self.loaded_content['content']
            for media_url in media_urls:
                if media_url is not None:
                    message.append(await make_forward_message_node('附件', bot.self_id, MessageSegment.image(file=media_url)))
        history_index = await group_setting.add_history(self.tweet_url)
        message.append(await make_forward_message_node('编号', bot.self_id, MessageSegment.text(text=f'编号：{history_index}')))
        return message

    async def send_message(self, bot: Bot, group_setting: GroupSetting):
        nonebot.logger.debug(
            f'making message for group {group_setting.group_id}')
        await self.load_screenshot_and_text()
        user_setting = await group_setting.get_user_setting(user_id=self.user_id)
        if user_setting is None:
            return
        if not getattr(user_setting, f'receive_{self.tweet_type}'):
            return
        if 'screenshot_path' not in self.loaded_content:
            await send_group_message(bot, group_setting.group_id, self.loaded_content['text'])
        nonebot.logger.debug(f'user_setting {await user_setting.to_json()}')
        if not user_setting.receive_collapsed_message:
            message = await self.make_normal_message(group_setting, user_setting)
            await send_group_message(bot, group_setting.group_id, message)
        else:
            messages = await self.make_forward_message(bot, group_setting, user_setting)
            await send_forward_message(bot, group_setting.group_id, messages)
        nonebot.logger.debug('send message finished')

    async def clean_up(self):
        screenshot_path = self.loaded_content.get('screenshot_path')
        if screenshot_path is not None and os.path.exists(screenshot_path):
            await remove(screenshot_path)
        nonebot.logger.debug(f'tweet {self.tweet_url} cleaned up')

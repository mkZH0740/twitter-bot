import json

import aiofiles
import nonebot
from nonebot import on_command
from nonebot import require
from nonebot.adapters.cqhttp import MessageSegment
from nonebot.adapters.cqhttp import Bot, GroupMessageEvent

from .utils import matcher_switch_group_setting, matcher_set_custom_setting, make_result_message, get_group_setting, send_translate_screenshot
from ..database import BotDatabase
from ..database.models import GroupSetting, UserSetting
from ..twitter import StreamHolder

database_dict = require('database')
bot_database: BotDatabase = database_dict.bot_database
twitter_dict = require('twitter')
stream_holder: StreamHolder = twitter_dict.stream_holder


get_group_setting_command = on_command('get')


@get_group_setting_command.handle()
async def get_group_setting_handler(bot: Bot, event: GroupMessageEvent, state):
    group_setting = await get_group_setting(get_group_setting_command, bot_database, event.group_id)
    user_settings = {user_id: await user.to_json_content() for user_id, user in group_setting.registered_users.items()}
    await get_group_setting_command.finish(json.dumps(user_settings, ensure_ascii=False, indent=2))


enable_user_setting_command = on_command('enable')


@enable_user_setting_command.handle()
async def enable_user_setting_handler(bot: Bot, event: GroupMessageEvent, state):
    await matcher_switch_group_setting(enable_user_setting_command, bot_database, event, True)


disable_user_setting_command = on_command('disable')


@disable_user_setting_command.handle()
async def disable_user_setting_handler(bot: Bot, event: GroupMessageEvent, state):
    await matcher_switch_group_setting(enable_user_setting_command, bot_database, event, False)


custom_user_setting_command = on_command('custom')


@custom_user_setting_command.handle()
async def custom_user_setting_handler(bot: Bot, event: GroupMessageEvent, state):
    if 'target' not in state:
        pair = str(event.get_message()).strip().split(';')
        if len(pair) != 2:
            await custom_user_setting_command.finish(f'invalid arg length {len(pair)}, expected 2')
        (target, key) = pair
        group_setting = await get_group_setting(custom_user_setting_command, bot_database, event.group_id)
        if target != '*' and (await group_setting.get_user(target)) is None:
            await custom_user_setting_command.finish(f'unknown user {target}')
        state['key'] = key
        state['target'] = target
        state['group_setting'] = group_setting


@custom_user_setting_command.got('content', prompt='please input your custom content')
async def custom_user_setting_content_handler(bot: Bot, event: GroupMessageEvent, state):
    await matcher_set_custom_setting(custom_user_setting_command, event.get_message()[0], state)


add_twitter_user_command = on_command('add')


@add_twitter_user_command.handle()
async def add_twitter_user_handler(bot: Bot, event: GroupMessageEvent, state):
    screen_name = str(event.get_message()).strip()
    group_setting = await get_group_setting(add_twitter_user_command, bot_database, event.group_id)
    (flag, content) = await stream_holder.get_user_by_screen_name(screen_name)
    if flag:
        result = await group_setting.add_user(content.id, screen_name)
        message = await make_result_message('user', result)
        if result[0]:
            await stream_holder.run_stream()
        await add_twitter_user_command.finish(message)
    else:
        await add_twitter_user_command.finish(f'unknown user {screen_name}')


delete_twitter_user_command = on_command('delete')


@delete_twitter_user_command.handle()
async def delete_twitter_user_handler(bot: Bot, event: GroupMessageEvent, state):
    screen_name = str(event.get_message()).strip()
    group_setting = await get_group_setting(delete_twitter_user_command, bot_database, event.group_id)
    (flag, content) = await stream_holder.get_user_by_screen_name(screen_name)
    if flag:
        result = await group_setting.delete_user(content.id)
        message = await make_result_message('user', result)
        if result[0]:
            await stream_holder.run_stream()
        await add_twitter_user_command.finish(message)
    else:
        await add_twitter_user_command.finish(f'unknown user {screen_name}')


translate_command = on_command('translate')


@translate_command.handle()
async def translate_handler(bot: Bot, event: GroupMessageEvent, state):
    if 'group_setting' not in state:
        raw_index = str(event.get_message()).strip()
        if not raw_index.isdigit():
            await translate_command.finish(f'invalid index {raw_index}, expected integer')
        group_setting = await get_group_setting(translate_command, bot_database, event.group_id)
        (flag, content) = await group_setting.get_history(int(raw_index))
        if not flag:
            await translate_command.finish(content)
        screen_name = content.split('/')[3]
        (flag, user) = await stream_holder.get_user_by_screen_name(screen_name)
        if not flag:
            await translate_command.finish(f'unknown user {screen_name}')
        if user.id not in group_setting.registered_users.keys():
            await translate_command.finish(f'unregistered user {screen_name}')
        user_setting = group_setting.registered_users[user.id]
        state['group_setting'] = group_setting
        state['user_setting'] = user_setting
        state['history_url'] = content


@translate_command.got('translation', prompt='please input translation block')
async def translate_block_handler(bot: Bot, event: GroupMessageEvent, state):
    user_setting: UserSetting = state['user_setting']
    history_url: str = state['history_url']
    await send_translate_screenshot(translate_command, history_url, user_setting, str(event.get_message()))


check_custom_command = on_command('check')


@check_custom_command.handle()
async def check_custom_handler(bot: Bot, event: GroupMessageEvent, state):
    group_setting = await get_group_setting(check_custom_command, bot_database, event.group_id)
    command = str(event.get_message()).strip()
    args = command.split(';')
    if len(args) != 2:
        await check_custom_command.finish(f'invalid arg length {len(args)}, expected 2')
    (screen_name, custom_name) = args
    (flag, user) = await stream_holder.get_user_by_screen_name(screen_name)
    if not flag:
        await check_custom_command.finish(f'unknown user {screen_name}')
    if user.id not in group_setting.registered_users.keys():
        await check_custom_command.finish(f'unregistered user {screen_name}')
    user_setting = group_setting.registered_users[user.id]
    custom_attr = f'custom_{custom_name}'
    if not hasattr(user_setting, custom_attr) or getattr(user_setting, custom_attr) is None:
        database_path = nonebot.get_driver().config.database_path
        if custom_name == 'css':
            file_path = f'{database_path}\\default\\default_css.css'
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            await check_custom_command.finish(content)
        elif custom_name == 'tag':
            file_path = f'{database_path}\\default\\default_tag.png'
            await check_custom_command.finish(MessageSegment.image(file=f'file:///{file_path}'))
        else:
            await check_custom_command.finish(f'unknown custom name {custom_name}')
    else:
        custom_content_path: str = getattr(user_setting, custom_attr)
        if custom_name == 'css':
            async with aiofiles.open(custom_content_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            await check_custom_command.finish(content)
        else:
            await check_custom_command.finish(MessageSegment.image(f'file:///{custom_content_path}'))

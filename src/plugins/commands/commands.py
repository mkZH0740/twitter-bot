import json

import nonebot
from nonebot import on_command
from nonebot import require
from nonebot.adapters.cqhttp import Bot, GroupMessageEvent

from .utils import matcher_switch_group_setting, matcher_set_custom_setting, make_result_message
from ..database import BotDatabase
from ..twitter import StreamHolder


database_dict = require('database')
bot_database: BotDatabase = database_dict.bot_database
twitter_dict = require('twitter')
stream_holder: StreamHolder = twitter_dict.stream_holder


get_group_setting_command = on_command('get')


@get_group_setting_command.handle()
async def get_group_setting_handler(bot: Bot, event: GroupMessageEvent, state):
    group_setting = await bot_database.get_group(event.group_id)
    if group_setting is None:
        await get_group_setting_command.finish(f'unknown group {event.group_id}')
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
        key: str = pair[0]
        target: str = pair[1]
        group_setting = await bot_database.get_group(event.group_id)
        nonebot.logger.debug(f'key = {key}, target = {target}')
        if group_setting is None:
            await custom_user_setting_command.finish(f'unknown group {event.group_id}')
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
    group_setting = await bot_database.get_group(event.group_id)
    if group_setting is None:
        await add_twitter_user_command.finish(f'unknown group {event.group_id}')
    try:
        user_id = await stream_holder.get_user_id_by_screen_name(screen_name)
        result = await group_setting.add_user(user_id, screen_name)
        flag = result[0]
        if flag:
            await stream_holder.run_stream()
        message = await make_result_message('user', result)
        await add_twitter_user_command.finish(message)
    except RuntimeError as e:
        await add_twitter_user_command.finish(str(e))


delete_twitter_user_command = on_command('delete')


@delete_twitter_user_command.handle()
async def delete_twitter_user_handler(bot: Bot, event: GroupMessageEvent, state):
    screen_name = str(event.get_message()).strip()
    group_setting = await bot_database.get_group(event.group_id)
    if group_setting is None:
        await add_twitter_user_command.finish(f'unknown group {event.group_id}')
    try:
        result = await group_setting.delete_user(screen_name)
        flag = result[0]
        if flag:
            await stream_holder.run_stream()
        message = await make_result_message('user', result)
        await add_twitter_user_command.finish(message)
    except RuntimeError as e:
        await add_twitter_user_command.finish(str(e))

import json

import aiofiles
from aiohttp.client_exceptions import ClientConnectionError
from nonebot import on_command, require
from nonebot.adapters.cqhttp import Bot, GroupMessageEvent, MessageSegment

from .utils import check_is_registered_group, check_args_length, check_custom_type, save_image_to_path, \
    matcher_switch_user_setting, matcher_send_translation_screenshot
from ..db import BotDatabase, GroupSetting
from ..db.models import custom_types
from ..twitter import StreamHolder


database_dict = require('db')
bot_database: BotDatabase = database_dict.bot_database
twitter_dict = require('twitter')
stream_holder: StreamHolder = twitter_dict.stream_holder


get_group_setting_command = on_command('get')
get_group_setting_command.__doc__ = """get: 获取当前群订阅的所有推特用户的设置，eg: #get"""


@get_group_setting_command.handle()
async def get_group_setting_handler(bot: Bot, event: GroupMessageEvent, state):
    group_setting = await check_is_registered_group(get_group_setting_command, event, bot_database)
    user_settings = {
        user_id: await user_setting.to_json_value() for user_id, user_setting in group_setting.registered_users.items()
    }
    await get_group_setting_command.finish(json.dumps(user_settings, ensure_ascii=False, indent=2))


enable_user_setting_command = on_command('enable')
enable_user_setting_command.__doc__ = """enable: 开启当前群订阅的推特用户设置，eg: #enable *;receive_tweet, #enable 
TAKATOSHI_Gship;receive_tweet\n\n所有可以设置的选项为receive_tweet, receive_retweet, receive_comment, receive_text, 
receive_translation, receive_screenshot, receive_content"""


@enable_user_setting_command.handle()
async def enable_user_setting_handler(bot: Bot, event: GroupMessageEvent, state):
    await matcher_switch_user_setting(enable_user_setting_command, event, bot_database, True)


disable_user_setting_command = on_command('disable')
disable_user_setting_command.__doc__ = """disable: 关闭当前群订阅的推特用户设置，eg: #disable *;receive_tweet, #disable 
TAKATOSHI_Gship;receive_tweet\n\n所有可以设置的选项为receive_tweet, receive_retweet, receive_comment, receive_text, 
receive_translation, receive_screenshot, receive_content"""


@disable_user_setting_command.handle()
async def disable_user_setting_handler(bot: Bot, event: GroupMessageEvent, state):
    await matcher_switch_user_setting(enable_user_setting_command, event, bot_database, False)


custom_user_setting_command = on_command('custom')
custom_user_setting_command.__doc__ = """custom: 设置当前群订阅的推特用户的定制内容，eg: #custom *;tag, #custom 
TAKATOSHI_Gship;tag\n\n所有可以设置的选项为tag, css, background """


@custom_user_setting_command.handle()
async def custom_user_setting_handler(bot: Bot, event: GroupMessageEvent, state):
    if 'screen_name' in state:
        return
    (screen_name, custom_key) = await check_args_length(custom_user_setting_command, event, ';', 2)
    group_setting = await check_is_registered_group(custom_user_setting_command, event, bot_database)
    if screen_name != '*' and (await group_setting.get_user_setting(screen_name=screen_name)) is None:
        await custom_user_setting_command.finish(f'未注册用户{screen_name}')
    state['group_setting'] = group_setting
    state['screen_name'] = screen_name
    state['custom_key'] = custom_key


@custom_user_setting_command.got('content', prompt='请输入自定义内容')
async def custom_content_handler(bot: Bot, event: GroupMessageEvent, state):
    group_setting: GroupSetting = state['group_setting']
    screen_name: str = state['screen_name']
    custom_key: str = state['custom_key']
    await check_custom_type(custom_user_setting_command, event, custom_key)
    custom_content = event.get_message()[0]
    if screen_name == '*':
        file_name = f'default_{custom_key}'
    else:
        (flag, user_setting) = await group_setting.get_user_setting(screen_name=screen_name)
        file_name = f'{user_setting.user_id}_{custom_key}'
    if custom_types[custom_key] == 'image':
        file_name += '.png'
        file_path = f'{group_setting.group_database_path}\\{file_name}'
        flag = await save_image_to_path(custom_content.data.get('url'), file_path)
        if not flag:
            await custom_user_setting_command.finish('下载图片失败')
    else:
        file_name += '.txt'
        file_path = f'{group_setting.group_database_path}\\{file_name}'
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(str(custom_content))
    if screen_name == '*':
        for user_setting in group_setting.registered_users.values():
            setattr(user_setting, f'custom_{custom_key}', file_path)
    else:
        (_, user_setting) = await group_setting.get_user_setting(screen_name=screen_name)
        setattr(user_setting, f'custom_{custom_key}', file_path)
    await custom_user_setting_command.finish('设置完成')


add_twitter_user_command = on_command('add')
add_twitter_user_command.__doc__ = """add: 在当前群订阅推特用户，eg: #add <screen name>，screen name可以在推特链接中找到，
（eg: https://twitter.com/TAKATOSHI_Gship， 则screen name为 TAKATOSHI_Gship，对应的命令为#add TAKATOSHI_Gship）"""


@add_twitter_user_command.handle()
async def add_twitter_user_handler(bot: Bot, event: GroupMessageEvent, state):
    screen_name = str(event.get_message()).strip()
    group_setting = await check_is_registered_group(add_twitter_user_command, event, bot_database)
    (flag, content) = await stream_holder.get_user_through_client(screen_name=screen_name)
    if flag:
        (flag, message) = await group_setting.register_user(content.id, screen_name)
        if flag:
            await stream_holder.run_stream()
        await add_twitter_user_command.finish(message)
    else:
        await add_twitter_user_command.finish('获取用户失败，请检查screen_name是否正确输入')


delete_twitter_user_command = on_command('delete')
delete_twitter_user_command.__doc__ = """delete: 在当前群删除订阅的推特用户,eg: #delete <screen name>，screen name可以在推特链接中找到，
（eg: https://twitter.com/TAKATOSHI_Gship， 则screen name为 TAKATOSHI_Gship，对应的命令为#delete TAKATOSHI_Gship）"""


@delete_twitter_user_command.handle()
async def delete_twitter_user_handler(bot: Bot, event: GroupMessageEvent, state):
    screen_name = str(event.get_message()).strip()
    group_setting = await check_is_registered_group(delete_twitter_user_command, event, bot_database)
    (flag, content) = await stream_holder.get_user_through_client(screen_name=screen_name)
    if flag:
        (flag, message) = await group_setting.unregister_user(user_id=content.id)
        if flag:
            await stream_holder.run_stream()
        await delete_twitter_user_command.finish(message)
    else:
        await delete_twitter_user_command.finish('获取用户失败，请检查screen_name是否正确输入')


translate_command = on_command('translate')
translate_command.__doc__ = """translate: 嵌字，需要对应的嵌字编号，eg: #translate 3，随后按照提示输入嵌字内容，如果是嵌入回复内容，需要指定行号，例如#1 第一行内容\n#3 
第三行内容 """


@translate_command.handle()
async def translate_handler(bot: Bot, event: GroupMessageEvent, state):
    if 'group_setting' in state:
        return
    index = str(event.get_message()).strip()
    if not index.isdigit():
        await translate_command.finish(f'非法参数，需要：int，当前：{index}')
    group_setting = await check_is_registered_group(translate_command, event, bot_database)
    (flag, content) = await group_setting.get_history(int(index))
    if not flag:
        await translate_command.finish(content)
    screen_name = content.split('/')[3]
    state['url'] = content
    (flag, user) = await stream_holder.get_user_through_client(screen_name=screen_name)
    if not flag:
        await translate_command.finish(f'未注册用户{screen_name}')
    (flag, user_setting) = await group_setting.get_user_setting(user_id=user.id)
    if not flag and user_setting is None:
        await translate_command.finish(f'未注册用户{screen_name}')
    elif isinstance(user_setting, str):
        await translate_command.finish(user_setting)
    state['user_setting'] = user_setting


@translate_command.got('translation', prompt='请输入翻译')
async def translation_handler(bot: Bot, event: GroupMessageEvent, state):
    try:
        await matcher_send_translation_screenshot(translate_command, event, state)
    except ClientConnectionError:
        await translate_command.finish('服务端未响应，请联系管理员')


check_custom_command = on_command('check')
check_custom_command.__doc__ = """check: 查询当前自定义的设置内容，eg: #check css, #check tag"""


@check_custom_command.handle()
async def check_custom_handler(bot: Bot, event: GroupMessageEvent, state):
    group_setting = await check_is_registered_group(check_custom_command, event, bot_database)
    (screen_name, custom_key) = await check_args_length(check_custom_command, event, ';', 2)
    (flag, user_setting) = await group_setting.get_user_setting(screen_name=screen_name)
    if user_setting is None:
        await check_custom_command.finish(f'未注册用户{screen_name}')
    elif isinstance(user_setting, str):
        await check_custom_command.finish(user_setting)
    if custom_key not in custom_types:
        await check_custom_command.finish(f'未知自定义属性{custom_key}')
    custom_content = getattr(user_setting, f'custom_{custom_key}') is None
    if custom_content is None:
        await check_custom_command.finish(f'没有对应属性')
    if custom_types[custom_key] == 'image':
        await check_custom_command.finish(MessageSegment.image(f'file:///{custom_content}'))
    else:
        async with aiofiles.open(custom_content, 'r', encoding='utf-8') as f:
            content = await f.read()
        await check_custom_command.finish(content)

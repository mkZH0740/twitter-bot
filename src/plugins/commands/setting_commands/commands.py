import json
import aiofiles

from nonebot.plugin import require, on_command
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Bot, GroupMessageEvent, MessageSegment

from ...database import Database, UserSetting, GroupSetting, custom_types
from ..utils import get_group_setting
from .utils import modify_user_setting, save_image_to_disk


database_dict = require('database')
database: Database = database_dict.database


get_group_setting_command = on_command('get')
get_group_setting_command.__doc__ = """get: 获取当前群订阅的所有推特用户的设置，eg: #get"""

@get_group_setting_command.handle()
async def get_group_setting_handler(bot: Bot, event: GroupMessageEvent, state: T_State):
    group_setting = await get_group_setting(get_group_setting_command, database, event.group_id)
    user_settings = {
        user_setting.screen_name: await user_setting.to_json() for user_setting in group_setting.user_settings.values()
    }
    await get_group_setting_command.finish(json.dumps(user_settings, ensure_ascii=False, indent=2))


enable_user_setting_command = on_command('enable')
enable_user_setting_command.__doc__ = """enable: 开启当前群订阅的推特用户设置，eg: #enable tweet, #enable 
TAKATOSHI_Gship;tweet\n\n所有可以设置的选项为tweet, retweet, comment, text, 
translation, screenshot, content"""

@enable_user_setting_command.handle()
async def enable_user_setting_handler(bot: Bot, event: GroupMessageEvent, state: T_State):
    await modify_user_setting(enable_user_setting_command, event, database, True)


disable_user_setting_command = on_command('disable')
disable_user_setting_command.__doc__ = """disable: 关闭当前群订阅的推特用户设置，eg: #disable tweet, #disable 
TAKATOSHI_Gship;tweet\n\n所有可以设置的选项为tweet, retweet, comment, text, 
translation, screenshot, content"""

@disable_user_setting_command.handle()
async def disable_user_setting_handler(bot: Bot, event: GroupMessageEvent, state: T_State):
    await modify_user_setting(disable_user_setting_command, event, database, False)


custom_user_setting_command = on_command('custom')
custom_user_setting_command.__doc__ = """custom: 设置当前群订阅的推特用户的定制内容，eg: #custom *;tag, #custom 
TAKATOSHI_Gship;tag\n\n所有可以设置的选项为tag, css, background """

@custom_user_setting_command.handle()
async def custom_user_setting_handler(bot: Bot, event: GroupMessageEvent, state: T_State):
    if 'screen_name' in state:
        return
    args = str(event.get_message()).strip().split(';')
    group_setting = await get_group_setting(custom_user_setting_command, database, event.group_id)
    match args:
        case [screen_name, key]:
            if key not in custom_types:
                await custom_user_setting_command.finish(f'未知自定义属性{key}，仅支持{custom_types.keys()}')
            if screen_name != '*':
                user_setting = await group_setting.get_user_setting(screen_name=screen_name)
                if user_setting is None:
                    await custom_user_setting_command.finish(f'未知用户{screen_name}')
                state['user_setting'] = user_setting
            state['group_setting'] = group_setting
            state['screen_name'] = screen_name
            state['key'] = key
        case _:
            await custom_user_setting_command.finish(f'参数个数非法，当前：{len(args)}，需要2')


@custom_user_setting_command.got('content', prompt='请输入自定义内容')
async def custom_content_handler(bot: Bot, event: GroupMessageEvent, state: T_State):
    group_setting: GroupSetting = state['group_setting']
    screen_name: str = state['screen_name']
    key: str = state['key']
    custom_message = event.get_message()[0]
    if custom_message.type != custom_types[key]:
        await custom_user_setting_command.finish(f'非法自定义类型，需要{custom_types[key]}，当前{custom_message.type}')
    if screen_name == '*':
        file_name = f'default_{key}'
    else:
        user_setting: UserSetting = state['user_setting']
        file_name = f'{user_setting.user_id}_{key}'
    if custom_message.type == 'image':
        file_name += '.png'
        file_path = f'{group_setting.group_database_path}\\{file_name}'
        flag = await save_image_to_disk(custom_message.data.get('url'), file_path)
        if not flag:
            await custom_user_setting_command.finish('下载图片失败')
    else:
        file_name += '.txt'
        file_path = f'{group_setting.group_database_path}\\{file_name}'
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(custom_message.data.get('text'))
    if screen_name == '*':
        for user_setting in group_setting.user_settings.values():
            setattr(user_setting, f'custom_{key}', file_path)
    else:
        setattr(user_setting, f'custom_{key}', file_path)
    await custom_user_setting_command.finish('设置完成')


check_custom_command = on_command('check')
check_custom_command.__doc__ = """check: 查询当前自定义的设置内容，eg: #check css, #check tag"""

@check_custom_command.handle()
async def check_custom_handler(bot: Bot, event: GroupMessageEvent, state: T_State):
    group_setting = await get_group_setting(check_custom_command, database, event.group_id)
    args = str(event.get_message()).strip().split(';')
    match args:
        case [screen_name, key]:
            user_setting = await group_setting.get_user_setting(screen_name=screen_name)
            if user_setting is None:
                await check_custom_command.finish(f'未注册用户{screen_name}')
            if key not in custom_types:
                await check_custom_command.finish(f'未知自定义属性{key}')
            custom_content = getattr(user_setting, f'custom_{key}')
            if custom_content is None:
                file_path = f'{database.database_path}\\default\\default_{key}'
                if custom_types[key] == 'image':
                    file_path += '.png'
                else:
                    file_path += '.txt'
            else:
                file_path = f'{group_setting.group_database_path}\\{custom_content}'
            if custom_types[key] == 'image':
                await check_custom_command.finish(MessageSegment.image(file=f'file:///{file_path}'))
            else:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                await check_custom_command.finish(content)

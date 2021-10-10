import nonebot
import aiohttp
from nonebot.adapters.cqhttp.message import MessageSegment

from nonebot.plugin import require, on_command
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Bot, GroupMessageEvent

from ..utils import get_group_setting
from ...database import Database, GroupSetting, UserSetting


database_dict = require('database')
database: Database = database_dict.database


translate_command = on_command('translate', aliases=set(['tr']))
translate_command.__doc__ = """translate或tr: 嵌字，需要对应的嵌字编号，eg: #translate 3，随后按照提示输入嵌字内容，如果是嵌入回复内容，需要指定行号，例如#1 第一行内容\n#3 
第三行内容 """


@translate_command.handle()
async def translate_handler(bot: Bot, event: GroupMessageEvent, state: T_State):
    if 'group_setting' in state:
        return
    index = str(event.get_message()).strip()
    if not index.isdigit():
        await translate_command.finish(f'非法参数类型，需要：int，当前：{index}')
    group_setting = await get_group_setting(translate_command, database, event.group_id)
    match await group_setting.get_history(int(index)):
        case[True, history]:
            screen_name = history.split('/')[3]
            user_setting = await group_setting.get_user_setting(screen_name=screen_name)
            if user_setting is None:
                await translate_command.finish(f'未注册用户{screen_name}')
            state['url'] = history
            state['user_setting'] = user_setting
            state['group_setting'] = group_setting
        case[False, message]:
            await translate_command.finish(message)


@translate_command.got('translation', prompt='请输入翻译')
async def translation_handler(bot: Bot, event: GroupMessageEvent, state: T_State):
    url: str = state['url']
    user_setting: UserSetting = state['user_setting']
    group_setting: GroupSetting = state['group_setting']
    translation = str(event.get_message()).replace('\r\n', '\n')
    config = nonebot.get_driver().config
    server_url: str = config.server_url
    server_path: str = config.server_path
    default_tag_path = f'{database.database_path}\\default\\default_tag.png'
    default_css_path = f'{database.database_path}\\default\\default_css.css'
    request_payload = {
        'url': url,
        'translation': translation,
        'custom': {
            'tag': default_tag_path,
            'css': default_css_path,
            'background': ''
        }
    }
    if user_setting.custom_tag is not None:
        request_payload['custom']['tag'] = f'{group_setting.group_database_path}\\{user_setting.custom_tag}'
    if user_setting.custom_css is not None:
        request_payload['custom']['css'] = f'{group_setting.group_database_path}\\{user_setting.custom_css}'
    if user_setting.custom_background is not None:
        request_payload['custom']['background'] = f'{group_setting.group_database_path}\\{user_setting.custom_background}'
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{server_url}/translate', json=request_payload) as response:
            if response.status != 200:
                await translate_command.finish(f'服务端未知错误{response.status}，请联系管理员')
            server_response: str = await response.json(encoding='utf-8')
            match server_response:
                case {'type': 'err', 'message': err_message}:
                    await translate_command.finish(err_message)
                case {'type': 'ok', 'screenshotPath': screenshot_path}:
                    await translate_command.finish(MessageSegment.image(file=f'file:///{server_path}\\{screenshot_path}'))
                case _:
                    await translate_command.finish(f'服务器未知错误，请联系管理员')

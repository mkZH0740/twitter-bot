import nonebot
from nonebot.rule import Rule
from nonebot.typing import T_State
from nonebot.plugin import on_message
from nonebot.adapters.cqhttp import Bot, GroupMessageEvent

from .models import PostGroupSettingReq
from ..database import GroupSetting


async def make_rule(group_id: int):
    async def check_confirmation(bot: Bot, event: GroupMessageEvent, state: T_State) -> bool:
        nonebot.logger.debug(f'receive message from {event.group_id}')
        flag = event.group_id == group_id and str(event.get_message()).strip() == 'confirm'
        nonebot.logger.debug(f'rule message {str(event.get_message()).strip()}')
        nonebot.logger.debug(f'rule result {flag}')
        return flag
    return Rule(check_confirmation)


async def register_matcher(group_setting: GroupSetting, post_group_setting_req: PostGroupSettingReq):
    matcher = on_message(rule=await make_rule(group_setting.group_id), temp=True)

    @matcher.handle()
    async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
        nonebot.logger.debug(f'receive message from {event.group_id}')
        user_setting = await group_setting.get_user_setting(int(post_group_setting_req.user_id))
        if user_setting is None:
            nonebot.logger.debug(f'网页端正试图设置一个不存在的用户{post_group_setting_req.screen_name}')
            await matcher.finish(f'网页端正试图设置一个不存在的用户{post_group_setting_req.screen_name}')
        for key, value in post_group_setting_req.settings.items():
            curr_value = getattr(user_setting, key)
            if isinstance(value, type(curr_value)) and value != curr_value:
                setattr(user_setting, key, value)
        nonebot.logger.debug(f'用户{user_setting.screen_name}设置已更新，当前设置为{await user_setting.to_json()}')
        await matcher.finish(f'用户{user_setting.screen_name}设置已更新，当前设置为{await user_setting.to_json()}')

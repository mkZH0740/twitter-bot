import nonebot

from nonebot.adapters.cqhttp import Bot, MessageSegment, ActionFailed


async def send_group_message(bot: Bot, group_id: int, message: str | MessageSegment):
    try:
        await bot.send_group_msg(group_id=group_id, message=message)
    except ActionFailed as e:
        nonebot.logger.warning(
            f'send to group {group_id} failed with retcode {e.info.get("retcode", "no-code")}')
    except Exception as e:
        nonebot.logger.warning(
            f'send to group {group_id} failed unknown error {e}')


async def send_private_message(bot: Bot, user_id: int, message: str | MessageSegment):
    try:
        await bot.send_private_msg(user_id=user_id, message=message)
    except ActionFailed as e:
        nonebot.logger.warning(
            f'send to user {user_id} failed with retcode {e.info.get("retcode", "no-code")}')
    except Exception as e:
        nonebot.logger.warning(
            f'send to user {user_id} failed unknown error {e}')


async def send_forward_message(bot: Bot, group_id: int, messages: list):
    try:
        await bot.call_api('send_group_forward_msg', group_id=group_id, messages=messages)
    except ActionFailed as e:
        nonebot.logger.warning(
            f'send to group {group_id} failed with retcode {e.info.get("retcode", "no-code")}')
    except Exception as e:
        nonebot.logger.warning(
            f'send to group {group_id} failed unknown error {e}')

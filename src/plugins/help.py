from nonebot.plugin import on_command
from nonebot.adapters.cqhttp import Bot, GroupMessageEvent
from nonebot.matcher import matchers

help_command = on_command('help')


@help_command.handle()
async def help_command_handler(bot: Bot, event: GroupMessageEvent, state):
    command_name = str(event.get_message()).strip()
    message = f'unknown command {command_name}'
    if command_name == '':
        message = ''
        for matcher_list in matchers.values():
            for matcher in matcher_list:
                if matcher.plugin_name.startswith('commands') and matcher.__doc__:
                    message += matcher.__doc__ + '\n'
    else:
        for matcher_list in matchers.values():
            for matcher in matcher_list:
                if matcher.plugin_name.startswith('commands') and matcher.__doc__ and matcher.__doc__.startswith(command_name):
                    message = matcher.__doc__
    await help_command.finish(message)

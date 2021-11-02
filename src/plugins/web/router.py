import nonebot
import inspect

from fastapi.exceptions import HTTPException
from nonebot.plugin import require
from fastapi import FastAPI

from ..database import Database, UserSetting
from .models import PostGroupSettingReq
from .utils import register_matcher


app: FastAPI = nonebot.get_app()

database_dict = require('database')
database: Database = database_dict.database


def invalid_value(value):
    return inspect.ismethod(value) or inspect.isasyncgenfunction(vars) or inspect.isfunction(value)


async def expand_user_setting(user_setting: UserSetting):
    args = [key for key in dir(user_setting) 
            if not key.startswith('_') and not invalid_value(getattr(user_setting, key))]
    result = {key: getattr(user_setting, key) for key in args}
    result['user_id'] = str(result['user_id'])
    return result


@app.get('/settings/{group_id}')
async def get_group_setting(group_id: int):
    group_setting = await database.get_group_setting(group_id)
    if group_setting is None:
        raise HTTPException(status_code=404, detail=f'不存在群{group_id}的设置')
    user_settings = [await expand_user_setting(user_setting) for user_setting in group_setting.user_settings.values()]
    return user_settings


@app.post('/settings/{group_id}')
async def post_group_setting(group_id: int, post_group_setting_req: PostGroupSettingReq):
    group_setting = await database.get_group_setting(group_id)
    if group_setting is None:
        raise HTTPException(status_code=404, detail=f'不存在群{group_id}的设置')
    await register_matcher(group_setting, post_group_setting_req)

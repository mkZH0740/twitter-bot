from pydantic import BaseModel


class PostGroupSettingReq(BaseModel):
    user_id: int
    screen_name: str
    settings: dict[str, bool]

from typing import Optional
from ..database.models import Group


class TweetUser:

    id: int
    screen_name: str

    def __init__(self, status):
        user = getattr(status, 'author')
        self.id = getattr(user, 'id')
        self.screen_name = getattr(user, 'screen_name')


class TweetEntities:

    media: list[dict]

    def __init__(self, status):
        entities: dict = getattr(status, 'extended_entities')
        self.media = entities.get('media')


class Tweet:

    id: int
    tweet_type: str
    user: TweetUser
    entities: TweetEntities

    text_message: Optional[str] = None
    translation_message: Optional[str] = None
    screenshot_message: Optional[str] = None
    content_message: Optional[str] = None

    def __init__(self, status):
        self.status = status
        self.id = getattr(status, 'id')
        self.user = TweetUser(status)
        self.entities = TweetEntities(status)
        self.tweet_type = 'tweet'
        if hasattr(status, 'retweeted_status'):
            self.tweet_type = 'retweet'
        elif getattr(status, 'in_reply_to_status_id') is not None:
            self.tweet_type = 'comment'

    async def load_text_and_screenshot_message(self):
        if self.screenshot_message is None:
            pass

    async def load_translation_message(self):
        if self.translation_message is None:
            pass

    async def load_content_message(self):
        if self.content_message is None:
            pass

    async def make_message(self, group: Group) -> str:
        pass

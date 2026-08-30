import asyncio

import requests
from zerolan.data.data.danmaku import Danmaku, SuperChat

from common.concurrent.abs_runnable import AsyncRunnable
from services.live_stream.config import YoutubeServiceConfig
from common.decorator import log_start, log_stop
from common.utils.str_util import is_blank
from event.event_data import LiveStreamDanmakuEvent, LiveStreamSuperChatEvent
from event.event_emitter import emitter

_DEFAULT_TIMEOUT = 30  # seconds


def get(url, token: str, session: requests.Session):
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json; charset=utf-8",
    }
    response = session.get(url, headers=headers, timeout=_DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.json()


def convert_danmakus(live_chat_messages: list[dict]):
    result = []
    for live_chat_message in live_chat_messages:
        if live_chat_message["type"] == "textMessageEvent":
            ts = live_chat_message["snippet"]["publishedAt"]
            content = live_chat_message["snippet"]["textMessageDetails"]["messageText"]
            uid = live_chat_message["snippet"]["authorDetails"]["channelId"]
            username = live_chat_message["snippet"]["authorDetails"]["displayName"]
            danmaku = Danmaku(uid=uid, username=username, content=content, ts=ts)
            result.append(danmaku)
    return result


def convert_superchats(super_chat_events: list[dict]):
    result = []
    for super_chat_event in super_chat_events:
        uid = super_chat_event["snippet"]["channelId"]
        username = super_chat_event["snippet"]["displayName"]
        ts = super_chat_event["snippet"]["createdAt"]
        content = super_chat_event["snippet"]["commentText"]
        money = super_chat_event["snippet"]["displayString"]
        sc = SuperChat(uid=uid, username=username, ts=ts, content=content, money=money)
        result.append(sc)
    return result


class YouTubeService(AsyncRunnable):
    def name(self):
        return "YouTubeService"

    def __init__(self, config: YoutubeServiceConfig):
        # TODO: Need test!
        super().__init__()
        if is_blank(config.token):
            raise ValueError("No token provided.")
        self._token = config.token
        self._danmakus = set()
        self._superchats = set()
        self._stop_flag = False
        self._session = requests.Session()

    async def _run(self):
        while not self._stop_flag:
            await asyncio.sleep(1)
            self.emit_danmaku_event()
            self.emit_super_chat_event()

    def emit_danmaku_event(self):
        # https://developers.google.com/youtube/v3/live/docs/liveChatMessages
        live_chat_messages = get("https://www.googleapis.com/youtube/v3/liveChat/messages", self._token, self._session)
        danmakus = set(convert_danmakus(live_chat_messages["items"]))
        updated_danmakus = danmakus.difference(self._danmakus)
        self._danmakus.update(updated_danmakus)
        for danmaku in updated_danmakus:
            emitter.emit(LiveStreamDanmakuEvent(danmaku=danmaku, platform="youtube"))

    def emit_super_chat_event(self):
        # https://developers.google.com/youtube/v3/live/docs/superChatEvents
        super_chat_events = get("https://www.googleapis.com/youtube/v3/superChatEvents", self._token, self._session)
        super_chats = set(convert_superchats(super_chat_events["items"]))
        updated_superchats = super_chats.difference(self._superchats)
        self._superchats.update(updated_superchats)
        for superchat in updated_superchats:
            emitter.emit(LiveStreamSuperChatEvent(superchat=superchat, platform="youtube"))

    @log_start("YouTubeService")
    async def start(self):
        await super().start()
        await self._run()

    @log_stop("YouTubeService")
    async def stop(self):
        await super().stop()
        self._stop_flag = True

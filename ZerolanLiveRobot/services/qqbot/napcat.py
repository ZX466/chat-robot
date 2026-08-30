import os
import time
from common.io.file_sys import fs

from loguru import logger


_napcat_initialized = False


def _ensure_napcat_env():
    """Lazily configure ncatbot environment. Called on first QQBotService instantiation."""
    global _napcat_initialized
    if _napcat_initialized:
        return

    napcat_dir = fs.temp_dir.joinpath('napcat')
    napcat_dir.mkdir(parents=True, exist_ok=True)
    napcat_log_dir = napcat_dir.joinpath('logs')
    napcat_log_dir.mkdir(parents=True, exist_ok=True)
    napcat_plugin_dir = napcat_dir.joinpath('plugins')
    napcat_plugin_dir.mkdir(parents=True, exist_ok=True)
    os.environ['NCATBOT_CONFIG_PATH'] = str(napcat_dir.joinpath('config.yaml'))
    os.environ['LOG_FILE_PATH'] = str(napcat_log_dir)

    from ncatbot.utils import ncatbot_config
    ncatbot_config.napcat.enable_webui = False
    ncatbot_config.plugin.skip_plugin_load = True
    ncatbot_config.plugin.plugins_dir = str(napcat_plugin_dir)

    _napcat_initialized = True


from typeguard import typechecked

from event.event_data import QQMessageEvent
from event.event_emitter import emitter
from services.qqbot.config import QQBotServiceConfig


class QQBotService:
    def __init__(self, config: QQBotServiceConfig):
        _ensure_napcat_env()

        from ncatbot.core import BotClient, GroupMessageEvent, PrivateMessageEvent
        self._bot = BotClient()
        self._api = self._bot.run_backend(bt_uin=config.qq_num, ws_uri=config.ws_uri,
                                          ws_token=config.ws_token, debug=False)
        self._root_user = config.root
        self._groups = config.groups if config.groups is not None else []
        logger.info("QQ bot started with Napcat backend.")
        self._last_sent_time = time.time()
        self._single_img_only: bool = True

        self._init()

    def _init(self):
        from ncatbot.core import GroupMessageEvent, PrivateMessageEvent

        @self._bot.on_group_message()
        async def echo_cmd(event: GroupMessageEvent):
            text = "".join(seg.text for seg in event.message.filter_text())
            if "echo" in text:
                if self.can_send():
                    await event.reply(text[4:])
                    self.set_timer()

        @self._bot.on_group_message()
        async def emit_plain_text_msg(event: GroupMessageEvent):
            if not (event.group_id in self._groups):
                return
            text = "".join(seg.text for seg in event.message.filter_text())
            images = event.message.filter_image()
            logger.debug(f"Received QQ message: {text}")
            if self.can_send():
                await self._emit_qq_msg(images, text, sender_id=str(event.sender.user_id), group_id=str(event.group_id))
                self.set_timer()

        @self._bot.on_private_message()
        async def on_private_message(event: PrivateMessageEvent):
            if str(event.sender.user_id) != str(self._root_user):
                return
            text = "".join(seg.text for seg in event.message.filter_text())
            images = event.message.filter_image()
            logger.debug(f"Received private QQ message: {text}")
            await self._emit_qq_msg(images, text, sender_id=str(event.sender.user_id), group_id=None)

    async def _emit_qq_msg(self, images, text, sender_id: str | None, group_id: str | None):
        if len(images) > 0:
            if self._single_img_only:
                image = images[0]
                img_path = fs.create_temp_file_descriptor(prefix='qqbot', suffix='.jpg', type='image')
                save_dir, filename = os.path.split(img_path)
                await image.download(save_dir, filename)
                if img_path.exists():
                    logger.debug(f"Received QQ image message: {img_path}")
                    self._emit_event(text=text, images=[img_path], group_id=group_id, sender_id=sender_id)
            else:
                logger.warning("Not implemented.")
        else:
            self._emit_event(text=text, group_id=group_id, sender_id=sender_id)

    def _emit_event(self, text: str, images: list | None = None,
                    group_id: str | None = None, sender_id: str | None = None):
        kwargs = {"message": text, "group_id": group_id, "sender_id": sender_id}
        if images is not None:
            kwargs["images"] = images
        emitter.emit(QQMessageEvent(**kwargs))

    def set_timer(self):
        self._last_sent_time = time.time()

    def can_send(self):
        now = time.time()
        logger.debug(f"Time since last send: {now - self._last_sent_time:.2f}s")
        if now - self._last_sent_time > 5:
            return True
        logger.warning("Limit sending QQ message.")
        return False

    @typechecked
    def send_plain_message(self, group_id: str | None, receiver_id: str | None, text: str):
        if receiver_id is None and group_id is None:
            raise ValueError("Either receiver_id or group_id must be provided")
        if group_id is not None:
            self._api.send_group_text_sync(group_id=group_id, text=text)
        else:
            self._api.send_private_plain_text_sync(user_id=receiver_id, text=text)
        logger.info(f"Sent QQ message: {text}")

    @typechecked
    def send_speech(self, group_id: str, audio_path: str):
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        self._api.send_group_record_sync(group_id, audio_path)

    def start(self):
        # self._api.send_private_text_sync(self._root_user, "hello")
        # self._bot.start()
        pass

    def stop(self):
        self._bot.bot_exit()

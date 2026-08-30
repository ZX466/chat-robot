import devices.headless
from agent.custom_agent import CustomAgent
from agent.tool_agent import ToolAgent
from character.filter.strategy import FirstMatchedFilter
from common.generator.gradio_gen import DynamicConfigPage
from devices.headless import is_headless
from devices.speaker import Speaker
from manager.config_manager import get_config
from manager.llm_prompt_manager import LLMPromptManager
from manager.model_manager import ModelManager
from manager.tts_prompt_manager import TTSPromptManager
from devices.microphone import SmartMicrophone
from pipeline.asr.asr_sync import ASRSyncPipeline
from pipeline.db.milvus.milvus_sync import MilvusSyncPipeline
from pipeline.imgcap.imgcap_sync import ImgCapSyncPipeline
from pipeline.llm.llm_sync import LLMSyncPipeline
from pipeline.ocr.ocr_sync import OCRSyncPipeline
from pipeline.tts.tts_sync import TTSSyncPipeline
from pipeline.vidcap.vidcap_sync import VidCapSyncPipeline
from pipeline.vla.showui.showui_sync import ShowUISyncPipeline
from services.browser.browser import Browser
from services.game.config import PlatformEnum
from services.game.minecraft.app import KonekoMinecraftAIAgent
from services.live_stream.bilibili import BilibiliService
from services.live_stream.twitch import TwitchService
from services.live_stream.youtube import YouTubeService
from services.obs.client import ObsStudioWsClient
from services.playground.bridge import PlaygroundBridge
from services.playground.res.res_server import ResourceServer


class ZerolanLiveRobotContext:
    """Initializes all context resources for the robot.

    Holds references to pipelines (LLM, ASR, TTS, OCR, etc.), services
    (OBS, Live2D, Browser, live-stream), and devices (microphone, speaker,
    keyboard). Event listener registration and event emission logic should
    NOT be placed here — that belongs in the Bot layer.
    """

    def __init__(self):
        config = get_config()

        # --- Core (always initialized) ---
        if not config.pipeline.llm.enable:
            raise ValueError("At least LLMPipeline must be enabled in your config.")

        self.llm: LLMSyncPipeline = LLMSyncPipeline(config.pipeline.llm)
        self.filter: FirstMatchedFilter = FirstMatchedFilter(config.character.chat.filter.bad_words)
        self.llm_prompt_manager: LLMPromptManager = LLMPromptManager(config.character.chat)
        self.tts_prompt_manager: TTSPromptManager | None = None
        self.speaker: Speaker = Speaker()
        self.bot_name: str = config.character.bot_name
        self.master_name: str = "AkagawaTsurunaki"
        self.res_server: ResourceServer = ResourceServer(config.service.res_server.host, config.service.res_server.port)
        self.tool_agent: ToolAgent = ToolAgent(config.pipeline.llm)

        # --- Screen (headless check at runtime) ---
        if not devices.headless.is_headless():
            from devices.screen.base_screen import Screen
            self.screen: Screen | None = Screen()
        else:
            self.screen = None

        # --- Optional pipelines (lazy defaults) ---
        self.asr: ASRSyncPipeline | None = None
        self.ocr: OCRSyncPipeline | None = None
        self.tts: TTSSyncPipeline | None = None
        self.img_cap: ImgCapSyncPipeline | None = None
        self.vid_cap: VidCapSyncPipeline | None = None
        self.showui: ShowUISyncPipeline | None = None
        self.vec_db: MilvusSyncPipeline | None = None

        # --- Optional services (lazy defaults) ---
        self.browser: Browser | None = None
        self.playground: PlaygroundBridge | None = None
        self.qq = None
        self.bot_id: str | None = None
        self.live2d_model: str | None = None
        self.live2d_viewer = None
        self.obs: ObsStudioWsClient | None = None
        self.game_agent = None
        self.bilibili: BilibiliService | None = None
        self.youtube: YouTubeService | None = None
        self.twitch: TwitchService | None = None
        self.model_manager: ModelManager | None = None
        self.keyboard = None
        self.custom_agent: CustomAgent | None = None
        self.config_page: DynamicConfigPage | None = None

        self._init_optional_components(config)

    def _init_optional_components(self, config):
        """Initialize optional components based on config flags."""
        if config.pipeline.asr.enable:
            self.asr = ASRSyncPipeline(config.pipeline.asr)
        if config.pipeline.ocr.enable:
            self.ocr = OCRSyncPipeline(config.pipeline.ocr)
        if config.pipeline.tts.enable:
            self.tts_prompt_manager = TTSPromptManager(config.character.speech)
            self.tts = TTSSyncPipeline(config.pipeline.tts)
        if config.pipeline.img_cap.enable:
            self.img_cap = ImgCapSyncPipeline(config.pipeline.img_cap)
        if config.pipeline.vid_cap.enable:
            self.vid_cap = VidCapSyncPipeline(config.pipeline.vid_cap)
        if config.pipeline.vla.enable and config.pipeline.vla.showui.enable:
            self.showui = ShowUISyncPipeline(config.pipeline.vla.showui)
        if config.service.browser.enable:
            self.browser = Browser(config.service.browser)
        if config.service.game.enable and config.service.game.platform == PlatformEnum.Minecraft:
            self.game_agent = KonekoMinecraftAIAgent(config.service.game, self.tool_agent)
        if config.service.live_stream.enable:
            if config.service.live_stream.bilibili.enable:
                self.bilibili = BilibiliService(config.service.live_stream.bilibili)
            if config.service.live_stream.youtube.enable:
                self.youtube = YouTubeService(config.service.live_stream.youtube)
            if config.service.live_stream.twitch.enable:
                self.twitch = TwitchService(config.service.live_stream.twitch)
        if config.pipeline.vec_db.enable:
            self.vec_db = MilvusSyncPipeline(config.pipeline.vec_db.milvus)
        if config.service.playground.enable:
            self.model_manager = ModelManager()
            self.bot_id = config.service.playground.bot_id
            self.live2d_model = config.service.playground.model_dir
            self.custom_agent = CustomAgent(config=config.pipeline.llm)
            self.playground = PlaygroundBridge(config=config.service.playground)
        if config.service.qqbot.enable:
            from services.qqbot.napcat import QQBotService
            self.qq: QQBotService = QQBotService(config.service.qqbot)

        self.mic = SmartMicrophone(enable_vad=config.system.default_enable_microphone, vad_mode=config.system.microphone_vad_mode)

        if not is_headless():
            from devices.keyboard import SmartKeyboard
            self.keyboard = SmartKeyboard(hotkeys=[config.system.microphone_hotkey])
        if config.service.obs.enable:
            self.obs = ObsStudioWsClient(config.service.obs)
        self.config_page = DynamicConfigPage(config)
        if config.service.live2d_viewer.enable:
            from services.live2d.live2d_viewer import Live2DViewer
            self.live2d_viewer = Live2DViewer(config.service.live2d_viewer)

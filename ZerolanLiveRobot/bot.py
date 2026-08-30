import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from queue import Queue
from typing import List

from loguru import logger
from zerolan.data.data.prompt import TTSPrompt
from zerolan.data.pipeline.img_cap import ImgCapQuery
from zerolan.data.pipeline.llm import LLMQuery, LLMPrediction
from zerolan.data.pipeline.milvus import MilvusInsert, InsertRow, MilvusQuery
from zerolan.data.pipeline.tts import TTSQuery

from agent.api import sentiment_analyse, summary_history, memory_score, sentiment_score
from common.concurrent.abs_runnable import stop_all_runnable
from common.concurrent.killable_thread import KillableThread, kill_all_threads
from common.enumerator import Language
from common.io.api import save_audio
from common.io.file_type import AudioFileType
from common.utils import audio_util, math_util
from common.utils.img_util import is_image_uniform
from event.event_data import PipelineOutputTTSEvent, PipelineOutputLLMEvent, SecondEvent
from event.event_emitter import emitter
from framework.base_bot import BaseBot
from handlers.event_handlers import register_all
from manager.config_manager import get_config

_config = get_config()


class ZerolanLiveRobot(BaseBot):
    """Main robot controller.

    Orchestrates all pipelines (ASR, LLM, TTS, OCR, etc.), services (OBS, Live2D,
    Browser, live-stream chat), and devices (microphone, speaker, keyboard) through
    an event-driven architecture powered by TypedEventEmitter.
    """

    def __init__(self):
        super().__init__()
        self.cur_lang = Language.ZH
        self.tts_prompt_manager.set_lang(self.cur_lang)
        self._timer_flag = True
        self.tts_thread_pool = ThreadPoolExecutor(max_workers=1)
        self.enable_exp_memory = _config.system.enable_intelligent_memory
        self.enable_sentiment_analysis = _config.system.enable_sentiment_analysis
        self.enable_split_by_punc = _config.system.enable_clause_split
        self.subtitles_queue = Queue()
        self.init()
        logger.info("🤖 Zerolan Live Robot: Initialized services successfully.")

    async def start(self):
        logger.info("🤖 Zerolan Live Robot: Running...")
        # Start emitter as a standalone task so it doesn't block the TaskGroup
        emitter_task = asyncio.create_task(emitter.start())
        async with asyncio.TaskGroup() as tg:
            if self.model_manager is not None:
                self.model_manager.scan()

            threads = []
            if _config.system.default_enable_microphone:
                vad_thread = KillableThread(target=self.mic.start, daemon=True, name="VADThread")
                threads.append(vad_thread)

            if self.keyboard is not None:
                keyboard_thread = KillableThread(target=self.keyboard.start, daemon=True, name="KeyboardThread")
                threads.append(keyboard_thread)

            speaker_thread = KillableThread(target=self.speaker.start, daemon=True, name="SpeakerThread")
            threads.append(speaker_thread)

            if self.playground:
                playground_thread = KillableThread(target=self.playground.start, daemon=True, name="PlaygroundThread")
                threads.append(playground_thread)

            if self.res_server:
                res_server_thread = KillableThread(target=self.res_server.start, daemon=True, name="ResServerThread")
                threads.append(res_server_thread)

            if self.obs is not None:
                obs_client_thread = KillableThread(target=self.obs.start, daemon=True, name="ObsClientThread")
                threads.append(obs_client_thread)

            if self.live2d_viewer is not None:
                live2d_viewer_thread = KillableThread(target=self.live2d_viewer.start, daemon=True,
                                                      name="Live2DViewerThread")
                threads.append(live2d_viewer_thread)

            if self.game_agent:
                game_agent_thread = KillableThread(target=self.game_agent.start, daemon=True, name="GameAgentThread")
                threads.append(game_agent_thread)

            for thread in threads:
                thread.start()

            if self.bilibili:
                def start_bili():
                    asyncio.run(self.bilibili.start())

                bili_thread = KillableThread(target=start_bili, daemon=True, name="BilibiliThread")
                bili_thread.start()
            if self.youtube:
                tg.create_task(self.youtube.start())
            if self.twitch:
                tg.create_task(self.twitch.start())
            if self.config_page:
                tg.create_task(self.config_page.start())
            elapsed = 0
            while self._timer_flag:
                await asyncio.sleep(1)
                emitter.emit(SecondEvent(elapsed=elapsed))
                elapsed += 1

        for thread in threads:
            thread.join()

    async def stop(self):
        self.tts_thread_pool.shutdown()
        await emitter.stop()
        kill_all_threads()
        await stop_all_runnable()
        logger.info("Good Bye!")

    def init(self):
        register_all(self)

    def _tts_without_block(self, tts_prompt: TTSPrompt | None, text: str):
        def wrapper():
            try:
                query = TTSQuery(
                    text=text,
                    text_language="auto",
                    refer_wav_path=tts_prompt.audio_path if tts_prompt else "",
                    prompt_text=tts_prompt.prompt_text if tts_prompt else "",
                    prompt_language=tts_prompt.lang if tts_prompt else "zh",
                    audio_type="wav"
                )
                prediction = self.tts.predict(query=query)
                logger.info(f"TTS: {query.text}")

                self.play_tts(PipelineOutputTTSEvent(prediction=prediction, transcript=text))
            except Exception as e:
                logger.error(f"TTS failed: {e}")

        # Check thread pool queue depth before submitting to avoid saturation
        pending = self.tts_thread_pool._work_queue.qsize()  # type: ignore[attr-defined]
        if pending >= 5:
            logger.warning(f"TTS thread pool queue depth is {pending}, skipping submission")
            return
        self.tts_thread_pool.submit(wrapper)

    def exp_memory(self, text: str, is_filtered: bool, response: str, len_history: int):

        l_max = get_config().character.chat.max_history
        try:
            s = sentiment_score(text)
        except Exception as e:
            logger.exception(e)
            s = 1

        if not is_filtered:
            b = 0
        else:
            b = self.filter.match(response)

        try:
            r = memory_score(response)
        except Exception as e:
            logger.exception(e)
            r = 1
        t_memory = 0.3 * (l_max - len_history) / l_max + 0.2 * s + 0.2 * b + 0.1 * r
        MEMORY_THRESHOLD = 0.5
        return t_memory > MEMORY_THRESHOLD

    def emit_llm_prediction(self, text, direct_return: bool = False) -> None | LLMPrediction:
        logger.debug("`emit_llm_prediction` called")
        query = LLMQuery(text=text, history=self.llm_prompt_manager.current_history)
        prediction = self.llm.predict(query)

        # Filter applied here
        is_filtered = self.filter.filter(prediction.response)

        if is_filtered:
            logger.warning(f"LLM (Filtered): {prediction.response}")
            return None

        # Remove leading \n
        if prediction.response and prediction.response[0] == '\n':
            prediction.response = prediction.response[1:]

        logger.info(f"Length of current history: {len(self.llm_prompt_manager.current_history)}")

        if self.enable_exp_memory:
            if self.exp_memory(text, is_filtered, prediction.response, len(self.llm_prompt_manager.current_history)):
                self.llm_prompt_manager.reset_history(prediction.history)
        else:
            # If experiment memory disabled, history should be updated for each chat commit.
            self.llm_prompt_manager.reset_history(prediction.history)

        if not direct_return:
            emitter.emit(PipelineOutputLLMEvent(prediction=prediction))
            logger.debug("LLMEvent emitted.")
        return prediction

    def change_lang(self, lang: Language):
        self.cur_lang = lang
        self.tts_prompt_manager.set_lang(lang.name())

    def check_img(self, img) -> bool:
        if is_image_uniform(img):
            logger.warning("Are you sure you capture the screen properly? The screen is black!")
            self.emit_llm_prediction("你忽然什么都看不见了！请向你的开发者求助！")
            return False
        return True

    def save_memory(self):
        start = len(self.llm_prompt_manager.injected_history)
        history = self.llm_prompt_manager.current_history[start:]
        ai_msg = summary_history(history)
        row = InsertRow(id=1, text=ai_msg.content, subject="history")
        insert = MilvusInsert(collection_name="history_collection", texts=[row])
        try:
            insert_res = self.vec_db.insert(insert)
            if insert_res.insert_count == 1:
                logger.info(f"Add a history memory: {row.text}")
            else:
                logger.warning(f"Failed to add a history memory.")
        except Exception as e:
            logger.warning(f"Milvus pipeline failed: {e}")

    def play_tts(self, event: PipelineOutputTTSEvent):
        prediction = event.prediction
        text = event.transcript
        self.subtitles_queue.put(text)
        audio_path = save_audio(wave_data=prediction.wave_data, format=AudioFileType(prediction.audio_type),
                                prefix='tts')
        if self.live2d_viewer:
            self.live2d_viewer.sync_lip(audio_path)
        if self.playground and self.playground.is_connected:
            self.playground.play_speech(bot_id=self.bot_id, audio_path=audio_path,
                                        transcript=text, bot_name=self.bot_name)
            logger.debug("Remote speaker enqueue speech data")
        else:
            # `playsound(audio_path, block=True)` will block the thread, use `enqueue_sound(audio_path)` instead
            self.speaker.enqueue_sound(audio_path)
            logger.debug("Local speaker enqueue speech data")

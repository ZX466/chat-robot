"""Event handler registrations — extracted from ZerolanLiveRobot.init()."""
import threading
from pathlib import Path
from typing import List

from loguru import logger
from zerolan.data.pipeline.asr import ASRStreamQuery
from zerolan.data.pipeline.img_cap import ImgCapQuery
from zerolan.data.pipeline.tts import TTSQuery

from agent.api import sentiment_analyse, translate
from common.enumerator import Language
from common.utils.str_util import split_by_punc, is_blank, sanitize_user_input, sanitize_user_input
from event.event_data import (
    DeviceMicrophoneVADEvent, DeviceKeyboardPressEvent, DeviceScreenCapturedEvent,
    PipelineOutputLLMEvent, PipelineImgCapEvent, QQMessageEvent,
    DeviceMicrophoneSwitchEvent, PipelineOutputTTSEvent, PipelineASREvent,
    PipelineOCREvent, ConfigFileModifiedEvent, LiveStreamDanmakuEvent,
    DeviceSpeakerPlayEvent,
)
from event.event_emitter import emitter
from event.registry import EventKeyRegistry
from handlers.asr_dispatch import dispatch_asr_command
from manager.config_manager import get_config
from pipeline.ocr.ocr_sync import avg_confidence, stringify
from zerolan.data.pipeline.ocr import OCRQuery

_config = get_config()


def register_all(bot):
    """Register all event handlers on the given bot instance."""

    # ASR result buffer: collect fragments and combine before sending to LLM
    _asr_buffer_lock = threading.Lock()
    _asr_buffer: list[str] = []
    _asr_timer: threading.Timer | None = None
    _ASR_BUFFER_WAIT = 1.5  # seconds to wait for more ASR results

    def _flush_asr_buffer():
        nonlocal _asr_timer
        with _asr_buffer_lock:
            _asr_timer = None
            if not _asr_buffer:
                return
            combined = "".join(_asr_buffer)
            _asr_buffer.clear()
        logger.info(f"ASR combined: {combined}")
        from zerolan.data.pipeline.asr import ASRPrediction
        emitter.emit(PipelineASREvent(prediction=ASRPrediction(transcript=combined)))

    @emitter.on(EventKeyRegistry.Playground.CONNECTED)
    def on_playground_connected(_):
        bot.mic.pause()
        logger.info("Because ZerolanPlayground client connected, close the local microphone.")
        if bot.playground:
            bot.playground.load_live2d_model(
                bot_id=bot.bot_id,
                bot_display_name=bot.bot_name,
                model_dir=bot.live2d_model
            )
        logger.info(f"Live 2D model loaded: {bot.live2d_model}")

    @emitter.on(EventKeyRegistry.Playground.DISCONNECTED)
    def on_playground_disconnected(_):
        pass

    @emitter.on(EventKeyRegistry.Device.KEYBOARD_HOTKEY_PRESS)
    def hotkey_handler(event: DeviceKeyboardPressEvent):
        logger.info(f'Hotkey toggle: {event.hotkey}')
        try:
            if event.hotkey == _config.system.microphone_hotkey:
                if _config.system.default_enable_microphone:
                    with bot.keyboard.microphone_state_lock:
                        if bot.mic.is_set_talk_enabled_event():
                            logger.debug('Hotkey toggled: MIC OFF')
                            bot.mic.unset_talk_enabled_event()
                            bot.mic.force_commit(is_emit=True)
                        else:
                            logger.debug('Hotkey toggled: MIC ON')
                            bot.mic.force_commit(is_emit=False)
                            bot.mic.set_talk_enabled_event()
                else:
                    logger.info('Microphone is disabled at config.yaml')
        except Exception as e:
            logger.exception(e)

    @emitter.on(EventKeyRegistry.Device.MICROPHONE_SWITCH)
    def on_open_microphone(event: DeviceMicrophoneSwitchEvent):
        if bot.mic.is_recording:
            if event.switch:
                logger.warning("The microphone has already resumed.")
                return
            bot.mic.pause()
        else:
            if not event.switch:
                logger.warning("The microphone has already paused.")
                return
            bot.mic.resume()

    @emitter.on(EventKeyRegistry.Device.MICROPHONE_VAD)
    def on_service_vad_speech_chunk(event: DeviceMicrophoneVADEvent):
        nonlocal _asr_timer
        logger.debug("`SpeechEvent` received.")
        speech, channels, sample_rate = event.speech, event.channels, event.sample_rate
        query = ASRStreamQuery(is_final=True, audio_data=speech, channels=channels, sample_rate=sample_rate,
                               media_type=event.audio_type.value)
        for prediction in bot.asr.stream_predict(query):
            logger.info(f"ASR: {prediction.transcript}")
            if is_blank(prediction.transcript):
                continue
            with _asr_buffer_lock:
                _asr_buffer.append(prediction.transcript)
                if _asr_timer is not None:
                    _asr_timer.cancel()
                _asr_timer = threading.Timer(_ASR_BUFFER_WAIT, _flush_asr_buffer)
                _asr_timer.daemon = True
                _asr_timer.start()
            logger.debug("ASR result buffered.")

    @emitter.on(EventKeyRegistry.Pipeline.ASR)
    def asr_handler(event: PipelineASREvent):
        logger.debug("`ASREvent` received.")
        prediction = event.prediction
        if bot.playground:
            bot.playground.add_history(role="user", text=prediction.transcript, username=bot.master_name)
        dispatch_asr_command(bot, prediction.transcript)
        if bot.playground:
            if bot.playground.is_connected:
                bot.playground.show_user_input_text(prediction.transcript)
        if bot.obs:
            bot.obs.subtitle(prediction.transcript, which="user")

    @emitter.on(EventKeyRegistry.LiveStream.DANMAKU)
    def on_danmaku(event: LiveStreamDanmakuEvent):
        safe_content = sanitize_user_input(event.danmaku.content)
        text = f'你收到了一条弹幕，用户"{event.danmaku.username}"说：\n{safe_content}'
        bot.emit_llm_prediction(text)

    @emitter.on(EventKeyRegistry.Device.SCREEN_CAPTURED)
    def on_device_screen_captured(event: DeviceScreenCapturedEvent):
        img_path = event.img_path
        if isinstance(event.img_path, Path):
            img_path = str(event.img_path)
        ocr_prediction = bot.ocr.predict(OCRQuery(img_path=img_path))
        if avg_confidence(ocr_prediction) > 0.6:
            logger.info("OCR: " + stringify(ocr_prediction.region_results))
            emitter.emit(PipelineOCREvent(prediction=ocr_prediction))
        else:
            img_cap_prediction = bot.img_cap.predict(ImgCapQuery(prompt="There", img_path=img_path))
            src_lang = Language.value_of(img_cap_prediction.lang)
            caption = translate(src_lang, bot.cur_lang, img_cap_prediction.caption)
            img_cap_prediction.caption = caption
            logger.info("ImgCap: " + caption)
            emitter.emit(PipelineImgCapEvent(prediction=img_cap_prediction))

    @emitter.on(EventKeyRegistry.QQBot.QQ_MESSAGE)
    def on_qq_message(event: QQMessageEvent):
        safe_message = sanitize_user_input(event.message)
        if "语音" in safe_message:
            prediction = bot.emit_llm_prediction(safe_message, direct_return=True)
            if prediction is None:
                logger.warning("No response from LLM remote service and will not send QQ message.")
                return
            tts_prompt = bot.tts_prompt_manager.default_tts_prompt
            query = TTSQuery(
                text=prediction.response,
                text_language="auto",
                refer_wav_path=tts_prompt.audio_path,
                prompt_text=tts_prompt.prompt_text,
                prompt_language=tts_prompt.lang,
                audio_type="wav"
            )
            tts_prediction = bot.tts.predict(query=query)
            from common.io.api import save_audio
            file_path = save_audio(tts_prediction.wave_data, prefix="tts")
            bot.qq.send_speech(event.group_id, str(file_path))
        elif event.images is not None and len(event.images) > 0:
            result = _predict_image_modal(bot, event.images)
            query_text = "你看见群友给你发了张图片，内容是：" + str(result)
            logger.info(f"OCR + ImgCap: {result}")
            prediction = bot.emit_llm_prediction(query_text, direct_return=True)
            if prediction is None:
                logger.warning("No response from LLM remote service and will not send QQ message.")
                return
            bot.qq.send_plain_message(group_id=event.group_id, receiver_id=event.sender_id,
                                       text=prediction.response)
        else:
            prediction = bot.emit_llm_prediction(safe_message, direct_return=True)
            if prediction is None:
                logger.warning("No response from LLM remote service and will not send QQ message.")
                return
            bot.qq.send_plain_message(group_id=event.group_id, receiver_id=event.sender_id,
                                       text=prediction.response)

    @emitter.on(EventKeyRegistry.Pipeline.OCR)
    def on_pipeline_ocr(event: PipelineOCREvent):
        prediction = event.prediction
        text = "你看见了" + stringify(prediction.region_results) + "\n请总结一下"
        bot.emit_llm_prediction(text)

    @emitter.on(EventKeyRegistry.Pipeline.IMG_CAP)
    def on_pipeline_img_cap(event: PipelineImgCapEvent):
        prediction = event.prediction
        text = "你看见了" + prediction.caption
        bot.emit_llm_prediction(text)

    @emitter.on(EventKeyRegistry.Pipeline.LLM)
    def llm_query_handler(event: PipelineOutputLLMEvent):
        prediction = event.prediction
        text = prediction.response
        logger.info("LLM: " + text)
        if bot.enable_sentiment_analysis:
            sentiment = sentiment_analyse(sentiments=bot.tts_prompt_manager.sentiments, text=text)
            tts_prompt = bot.tts_prompt_manager.get_tts_prompt(sentiment)
        else:
            tts_prompt = bot.tts_prompt_manager.default_tts_prompt
        if bot.playground:
            bot.playground.add_history(role="assistant", text=text, username=bot.bot_name)
        if bot.enable_split_by_punc:
            transcripts = split_by_punc(text, bot.cur_lang)
            if len(transcripts) > 0:
                for idx, transcript in enumerate(transcripts):
                    bot._tts_without_block(tts_prompt, transcript)
        else:
            bot._tts_without_block(tts_prompt, text)

    @emitter.on(EventKeyRegistry.System.CONFIG_FILE_MODIFIED)
    def on_config_modified(_: ConfigFileModifiedEvent):
        get_config()

    @emitter.on(EventKeyRegistry.Device.SPEAKER_PLAY)
    def on_speaker_play(event: DeviceSpeakerPlayEvent):
        if bot.obs is not None:
            if not event.audio_path.exists():
                logger.warning(f"Audio file does not exist: {event.audio_path}")
                return
            from common.utils import audio_util, math_util
            sample_rate, num_channels, duration = audio_util.get_audio_info(event.audio_path)
            text = bot.subtitles_queue.get()
            bot.obs.subtitle(text, which="assistant", duration=math_util.clamp(0, 5, duration - 1))


def _predict_image_modal(bot, images: List[Path]):
    results = []
    for image in images:
        if image.exists():
            ocr_prediction = bot.ocr.predict(OCRQuery(img_path=str(image)))
            ocr_text = stringify(ocr_prediction.region_results)
            img_cap_prediction = bot.img_cap.predict(ImgCapQuery(prompt="There", img_path=str(image)))
            img_cap_text = img_cap_prediction.caption
            results.append({
                "ocr": ocr_text,
                "sentiment": img_cap_text
            })
    return results

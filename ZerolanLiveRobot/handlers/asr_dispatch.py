"""ASR command dispatch table — replaces 12-elif chain with pattern matching."""
import os

from loguru import logger
from zerolan.data.pipeline.milvus import MilvusQuery

from agent.api import find_file, model_scale
from event.event_data import DeviceScreenCapturedEvent
from event.event_emitter import emitter
from zerolan.data.pipeline.vla import ShowUiQuery


def _handle_browser_open(bot, transcript: str):
    if bot.browser is not None:
        bot.browser.open("https://www.bing.com")


def _handle_browser_close(bot, transcript: str):
    if bot.browser is not None:
        bot.browser.close()


def _handle_browser_search(bot, transcript: str):
    if bot.browser is not None:
        text = transcript[4:]
        bot.browser.search(text)


def _handle_game(bot, transcript: str):
    bot.game_agent.exec_instruction(transcript)


def _handle_see(bot, transcript: str):
    img, img_save_path = bot.screen.safe_capture(k=0.99)
    if not bot.check_img(img):
        return
    emitter.emit(DeviceScreenCapturedEvent(img_path=img_save_path, is_camera=False))


def _handle_click(bot, transcript: str):
    if os.environ.get('DISPLAY', None) is None:
        return
    img, img_save_path = bot.screen.safe_capture(k=0.99)
    if not bot.check_img(img):
        return
    query = ShowUiQuery(query=transcript, env="web", img_path=img_save_path)
    prediction = bot.showui.predict(query)
    logger.debug("ShowUI: " + prediction.model_dump_json())
    action = prediction.actions[0]
    if action.action == "CLICK":
        import pyautogui
        logger.info("Click action triggered.")
        x, y = action.position[0] * img.width, action.position[1] * img.height
        pyautogui.moveTo(x, y)
        pyautogui.click()


def _handle_remember(bot, transcript: str):
    query = MilvusQuery(collection_name="history_collection", limit=2, output_fields=['history', 'text'],
                        query=transcript)
    result = bot.vec_db.search(query)
    memory = result.result[0][0]
    memory = memory.entity["text"]
    logger.debug(f"Memory found: {memory}")
    bot.emit_llm_prediction(f"{memory}\n\n请根据上文回答：{transcript} \n")


def _handle_load_model(bot, transcript: str):
    file_id = find_file(bot.model_manager.get_files(), transcript)
    file_info = bot.model_manager.get_file_by_id(file_id)
    if bot.playground:
        bot.playground.load_3d_model(file_info)


def _handle_adjust_model(bot, transcript: str):
    if bot.playground:
        info = bot.playground.get_gameobjects_info()
        if not info:
            logger.warning("No gameobjects info")
            return
        so = model_scale(info, transcript)
        bot.playground.modify_game_object_scale(so)


def _handle_default(bot, transcript: str):
    if bot.playground:
        if bot.custom_agent is None:
            raise RuntimeError("custom_agent must be initialized before use")
        tool_called = bot.custom_agent.run(transcript)
        if tool_called:
            logger.debug("Tool called.")
    bot.emit_llm_prediction(transcript)


# Dispatch table: (keyword, handler) — first match wins
_COMMAND_TABLE = [
    ("打开浏览器", _handle_browser_open),
    ("关闭浏览器", _handle_browser_close),
    ("网页搜索", _handle_browser_search),
    ("游戏", _handle_game),
    ("看见", _handle_see),
    ("点击", _handle_click),
    ("记得", _handle_remember),
    ("加载模型", _handle_load_model),
    ("调整模型", _handle_adjust_model),
]


def dispatch_asr_command(bot, transcript: str):
    """Dispatch ASR transcript to the first matching command handler."""
    for keyword, handler in _COMMAND_TABLE:
        if keyword in transcript:
            handler(bot, transcript)
            return
    _handle_default(bot, transcript)

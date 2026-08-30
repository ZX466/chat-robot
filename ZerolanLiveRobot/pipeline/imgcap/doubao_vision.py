import base64
import os
from typing import Generator

import requests
from loguru import logger
from typeguard import typechecked
from zerolan.data.pipeline.img_cap import ImgCapQuery, ImgCapPrediction

from pipeline.imgcap.config import DoubaoVisionConfig


class DoubaoVisionPipeline:
    def __init__(self, config: DoubaoVisionConfig):
        self._api_key = config.api_key or os.environ.get("ARK_API_KEY", "")
        self._api_url = config.api_url
        self._model = config.model

    @typechecked
    def predict(self, query: ImgCapQuery) -> ImgCapPrediction:
        if not self._api_key:
            raise ValueError("Doubao Vision API key must be provided!")

        img_path = query.img_path
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Image file not found: {img_path}")

        with open(img_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")

        prompt = query.prompt if query.prompt else "你看见了什么？请详细描述图片内容。"

        payload = {
            "model": self._model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{img_base64}"
                        },
                        {
                            "type": "input_text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(self._api_url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()

        caption = self._extract_caption(result)
        logger.info(f"DoubaoVision image caption: {caption}")

        lang = self._detect_lang(caption)
        return ImgCapPrediction(caption=caption, lang=lang)

    @typechecked
    def stream_predict(self, query: ImgCapQuery, chunk_size: int | None = None) -> Generator[
        ImgCapPrediction, None, None]:
        prediction = self.predict(query)
        yield prediction

    @staticmethod
    def _extract_caption(result: dict) -> str:
        try:
            output = result.get("output", [])
            for item in output:
                if item.get("type") == "message":
                    content_list = item.get("content", [])
                    for content in content_list:
                        if content.get("type") == "output_text":
                            return content.get("text", "")

            choices = result.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "")
                if isinstance(content, str):
                    return content
                elif isinstance(content, list):
                    texts = [c.get("text", "") for c in content if c.get("type") in ("text", "output_text")]
                    return " ".join(texts)
        except Exception as e:
            logger.warning(f"Failed to parse DoubaoVision response: {e}")

        return str(result)

    @staticmethod
    def _detect_lang(text: str) -> str:
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return "zh"
            elif '\u3040' <= char <= '\u309f' or '\u30a0' <= char <= '\u30ff':
                return "ja"
            elif '\uac00' <= char <= '\ud7af':
                return "ko"
        return "en"

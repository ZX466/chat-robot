import os

import requests
from loguru import logger
from typeguard import typechecked
from zerolan.data.pipeline.llm import LLMQuery, LLMPrediction, RoleEnum, Conversation

from pipeline.llm.config import DoubaoArkConfig


class DoubaoArkLLMPipeline:
    def __init__(self, config: DoubaoArkConfig):
        self._api_key = config.api_key or os.environ.get("ARK_API_KEY", "")
        self._api_url = config.api_url
        self._model = config.model

    @typechecked
    def predict(self, query: LLMQuery) -> LLMPrediction:
        if not self._api_key:
            raise ValueError("Doubao Ark API key must be provided!")

        input_messages = []
        for chat in query.history:
            input_messages.append({
                "role": chat.role,
                "content": [{"type": "input_text", "text": chat.content}]
            })
        input_messages.append({
            "role": "user",
            "content": [{"type": "input_text", "text": query.text}]
        })

        payload = {
            "model": self._model,
            "input": input_messages
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(self._api_url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json()
        text = self._extract_text(result)
        logger.info(f"DoubaoArk response: {text}")

        query.history.append(Conversation(role=RoleEnum.user, content=query.text))
        query.history.append(Conversation(role=RoleEnum.assistant, content=text))
        return LLMPrediction(response=text, history=query.history)

    @typechecked
    def stream_predict(self, query: LLMQuery, chunk_size: int | None = None):
        raise NotImplementedError("DoubaoArk stream prediction is not supported.")

    @staticmethod
    def _extract_text(result: dict) -> str:
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
            logger.warning(f"Failed to parse DoubaoArk response: {e}")

        return str(result)

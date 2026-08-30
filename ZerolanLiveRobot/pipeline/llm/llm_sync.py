from openai import OpenAI
from requests import Response
from typeguard import typechecked
from zerolan.data.pipeline.llm import LLMQuery, LLMPrediction, RoleEnum, Conversation

from pipeline.base.base_sync import CommonModelPipeline
from pipeline.llm.config import LLMPipelineConfig, LLMModelIdEnum
from pipeline.llm.doubao_ark_llm import DoubaoArkLLMPipeline


def _to_openai_format(query: LLMQuery):
    messages = []
    for chat in query.history:
        messages.append({
            "role": chat.role,
            "content": chat.content
        })
    messages.append({
        "role": "user",
        "content": query.text
    })
    return messages


def _append_history(query: LLMQuery, response: str):
    query.history.append(Conversation(role=RoleEnum.user, content=query.text))
    query.history.append(Conversation(role=RoleEnum.assistant, content=response))


def _openai_predict(query: LLMQuery, wrapper):
    messages = _to_openai_format(query)
    completion = wrapper(messages)
    resp = completion.choices[0].message.content
    _append_history(query, resp)
    return LLMPrediction(response=resp, history=query.history)


def _openai_stream_predict(query: LLMQuery, wrapper):
    messages = _to_openai_format(query)
    stream = wrapper(messages)

    full_response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response += content

            history_copy = list(query.history)
            history_copy.append(Conversation(role=RoleEnum.user, content=query.text))
            history_copy.append(Conversation(role=RoleEnum.assistant, content=full_response))
            yield LLMPrediction(response=full_response, history=history_copy)

    _append_history(query, full_response)


# Per-model default kwargs for chat.completions.create
_MODEL_DEFAULTS = {
    "moonshot-v1-8k": {"temperature": 0.3},
}


def _build_wrapper(client: OpenAI, model_id: str, stream: bool):
    """Build a chat completion wrapper for any OpenAI-compatible model."""
    defaults = _MODEL_DEFAULTS.get(model_id, {})

    def wrapper(messages):
        return client.chat.completions.create(
            model=model_id,
            messages=messages,
            stream=stream,
            **defaults,
        )

    return wrapper


class LLMSyncPipeline(CommonModelPipeline):

    def __init__(self, config: LLMPipelineConfig):
        super().__init__(config)
        self._is_openai_format = config.openai_format
        if self._is_openai_format:
            if not (config.predict_url and config.stream_predict_url):
                raise ValueError("Please provide `predict_url` or `stream_predict_url`")
            base_url = config.predict_url if config.predict_url else config.stream_predict_url
            self._remote_model = OpenAI(api_key=config.api_key, base_url=base_url)

        if config.model_id == LLMModelIdEnum.DoubaoArk and config.doubao_ark_config is not None:
            self._doubao_ark = DoubaoArkLLMPipeline(config=config.doubao_ark_config)
            self.predict = self._doubao_ark.predict
            self.stream_predict = self._doubao_ark.stream_predict

    @typechecked
    def predict(self, query: LLMQuery) -> LLMPrediction | None:
        if self._is_openai_format:
            wrapper = _build_wrapper(self._remote_model, self.model_id, stream=False)
            return _openai_predict(query, wrapper)
        else:
            return super().predict(query)

    @typechecked
    def stream_predict(self, query: LLMQuery, chunk_size: int | None = None):
        if self._is_openai_format:
            wrapper = _build_wrapper(self._remote_model, self.model_id, stream=True)
            return _openai_stream_predict(query, wrapper)
        else:
            return super().stream_predict(query, chunk_size)

    def parse_prediction(self, response: Response) -> LLMPrediction:
        json_val = response.content
        return LLMPrediction.model_validate_json(json_val)

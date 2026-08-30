"""Unit tests for pipeline implementations (ASR, TTS, LLM, OCR, Milvus)."""
import os
import tempfile
from unittest.mock import MagicMock, patch, PropertyMock
from typing import List

import pytest
from requests import Response

from zerolan.data.pipeline.llm import LLMQuery, LLMPrediction, Conversation, RoleEnum
from zerolan.data.pipeline.ocr import OCRPrediction, RegionResult, Position, Vector2D
from zerolan.data.pipeline.tts import TTSQuery, TTSPrediction

from pipeline.ocr.ocr_sync import avg_confidence, stringify


def _make_region(content: str, confidence: float) -> RegionResult:
    p = Position(
        lu=Vector2D(x=0, y=0), ru=Vector2D(x=1, y=0),
        rd=Vector2D(x=1, y=1), ld=Vector2D(x=0, y=1),
    )
    return RegionResult(position=p, content=content, confidence=confidence)


# --- OCR pure functions ---

@pytest.mark.unit
class TestAvgConfidence:
    def test_empty_results(self):
        pred = OCRPrediction(region_results=[])
        assert avg_confidence(pred) == 0

    def test_single_result(self):
        pred = OCRPrediction(region_results=[_make_region("hello", 0.9)])
        assert avg_confidence(pred) == pytest.approx(0.9)

    def test_multiple_results(self):
        regions = [_make_region("a", 0.8), _make_region("b", 0.6)]
        pred = OCRPrediction(region_results=regions)
        assert avg_confidence(pred) == pytest.approx(0.7)


@pytest.mark.unit
class TestStringify:
    def test_empty_list(self):
        assert stringify([]) == ""

    def test_single_region(self):
        regions = [_make_region("hello", 0.9)]
        result = stringify(regions)
        assert "[0] hello" in result

    def test_multiple_regions(self):
        regions = [_make_region("line1", 0.9), _make_region("line2", 0.8)]
        result = stringify(regions)
        assert "[0] line1" in result
        assert "[1] line2" in result

    def test_non_list_raises(self):
        with pytest.raises(TypeError, match="must be a list"):
            stringify("not a list")

    def test_non_region_result_raises(self):
        with pytest.raises(TypeError, match="Each item must be a RegionResult"):
            stringify(["not a region"])


# --- LLM _to_openai_format ---

@pytest.mark.unit
class TestToOpenaiFormat:
    def test_empty_history(self):
        from pipeline.llm.llm_sync import _to_openai_format
        query = LLMQuery(text="hello", history=[])
        messages = _to_openai_format(query)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "hello"

    def test_with_history(self):
        from pipeline.llm.llm_sync import _to_openai_format
        history = [
            Conversation(role=RoleEnum.user, content="hi"),
            Conversation(role=RoleEnum.assistant, content="hello"),
        ]
        query = LLMQuery(text="bye", history=history)
        messages = _to_openai_format(query)
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "hi"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "hello"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "bye"


# --- LLM predict (mocked OpenAI) ---

@pytest.mark.unit
class TestLLMSyncPipelinePredict:
    def test_predict_openai_format(self):
        from pipeline.llm.llm_sync import LLMSyncPipeline
        from pipeline.llm.config import LLMPipelineConfig

        mock_choice = MagicMock()
        mock_choice.message.content = "I am a test response"
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        config = LLMPipelineConfig(
            model_id="deepseek-chat",
            predict_url="https://api.deepseek.com",
            stream_predict_url="https://api.deepseek.com",
            api_key="test-key",
            openai_format=True,
        )

        pipeline = LLMSyncPipeline(config)
        pipeline._remote_model = MagicMock()
        pipeline._remote_model.chat.completions.create.return_value = mock_completion

        query = LLMQuery(text="hello", history=[])
        result = pipeline.predict(query)

        assert isinstance(result, LLMPrediction)
        assert result.response == "I am a test response"
        assert len(result.history) == 2
        assert result.history[0].role == RoleEnum.user
        assert result.history[1].role == RoleEnum.assistant

    def test_predict_unsupported_model_raises(self):
        from pipeline.llm.llm_sync import LLMSyncPipeline
        from pipeline.llm.config import LLMPipelineConfig

        config = LLMPipelineConfig(
            model_id="THUDM/chatglm3-6b",
            predict_url="https://api.example.com",
            stream_predict_url="https://api.example.com",
            api_key="test-key",
            openai_format=True,
        )

        pipeline = LLMSyncPipeline(config)
        query = LLMQuery(text="hello", history=[])

        with pytest.raises(NotImplementedError, match="Unsupported model"):
            pipeline.predict(query)


# --- ASR parse_query ---

@pytest.mark.unit
class TestASRParseQuery:
    def test_parse_stream_query(self):
        from pipeline.asr.asr_sync import ASRSyncPipeline
        from pipeline.asr.config import ASRPipelineConfig
        from zerolan.data.pipeline.asr import ASRStreamQuery

        config = ASRPipelineConfig()
        pipeline = ASRSyncPipeline(config)

        query = ASRStreamQuery(
            is_final=True,
            audio_data=b"\x00\x00\x00\x00",
            channels=1,
            sample_rate=16000,
            media_type="wav",
        )
        files, data = pipeline.parse_query(query)
        assert "audio" in files
        assert "json" in data

    def test_parse_stream_query_empty_audio_raises(self):
        from pipeline.asr.asr_sync import ASRSyncPipeline
        from pipeline.asr.config import ASRPipelineConfig
        from zerolan.data.pipeline.asr import ASRStreamQuery

        config = ASRPipelineConfig()
        pipeline = ASRSyncPipeline(config)

        query = ASRStreamQuery(
            is_final=True,
            audio_data=b"",
            channels=1,
            sample_rate=16000,
            media_type="wav",
        )
        with pytest.raises(ValueError, match="audio_data must not be empty"):
            pipeline.parse_query(query)

    def test_parse_query_with_local_file(self):
        from pipeline.asr.asr_sync import ASRSyncPipeline
        from pipeline.asr.config import ASRPipelineConfig
        from zerolan.data.pipeline.asr import ASRQuery

        config = ASRPipelineConfig()
        pipeline = ASRSyncPipeline(config)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF" + b"\x00" * 100)
            audio_path = f.name

        try:
            query = ASRQuery(audio_path=audio_path)
            files, data = pipeline.parse_query(query)
            assert files is not None
            assert "audio" in files
            assert "json" in data
        finally:
            os.unlink(audio_path)


# --- MilvusSyncPipeline ---

@pytest.mark.unit
class TestMilvusSyncPipeline:
    def test_init(self):
        from pipeline.db.milvus.milvus_sync import MilvusSyncPipeline, MilvusDatabaseConfig

        config = MilvusDatabaseConfig(
            insert_url="http://localhost:9999/insert",
            search_url="http://localhost:9999/search",
        )
        pipeline = MilvusSyncPipeline(config)
        assert pipeline.insert_url == "http://localhost:9999/insert"
        assert pipeline.search_url == "http://localhost:9999/search"

    def test_disabled_raises(self):
        from pipeline.db.milvus.milvus_sync import MilvusSyncPipeline, MilvusDatabaseConfig
        from pipeline.base.base_sync import PipelineDisabledException

        config = MilvusDatabaseConfig(enable=False)
        with pytest.raises(PipelineDisabledException):
            MilvusSyncPipeline(config)

    @patch("pipeline.db.milvus.milvus_sync.requests.post")
    def test_insert_calls_post(self, mock_post):
        from pipeline.db.milvus.milvus_sync import MilvusSyncPipeline, MilvusDatabaseConfig
        from zerolan.data.pipeline.milvus import MilvusInsert, MilvusInsertResult, InsertRow

        mock_response = MagicMock()
        mock_response.json.return_value = {"insert_count": 1, "ids": [1]}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        config = MilvusDatabaseConfig()
        pipeline = MilvusSyncPipeline(config)

        insert = MilvusInsert(collection_name="test", texts=[InsertRow(id=1, text="hello", subject="test")])
        result = pipeline.insert(insert)

        mock_post.assert_called_once()
        assert isinstance(result, MilvusInsertResult)
        assert result.insert_count == 1

    @patch("pipeline.db.milvus.milvus_sync.requests.post")
    def test_search_calls_post(self, mock_post):
        from pipeline.db.milvus.milvus_sync import MilvusSyncPipeline, MilvusDatabaseConfig
        from zerolan.data.pipeline.milvus import MilvusQuery, MilvusQueryResult

        mock_response = MagicMock()
        mock_response.json.return_value = {"result": []}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        config = MilvusDatabaseConfig()
        pipeline = MilvusSyncPipeline(config)

        query = MilvusQuery(collection_name="test", limit=5, output_fields=["text"], query="hello")
        result = pipeline.search(query)

        mock_post.assert_called_once()
        assert isinstance(result, MilvusQueryResult)


# --- TTS predict (mocked HTTP) ---

@pytest.mark.unit
class TestTTSSyncPipelinePredict:
    @patch("pipeline.tts.tts_sync.requests.post")
    def test_predict_returns_prediction(self, mock_post):
        from pipeline.tts.tts_sync import TTSSyncPipeline
        from pipeline.tts.config import TTSPipelineConfig

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"RIFF....wavdata"
        mock_post.return_value = mock_response

        config = TTSPipelineConfig()
        pipeline = TTSSyncPipeline(config)

        query = TTSQuery(
            text="hello world",
            text_language="auto",
            refer_wav_path="",
            prompt_text="",
            prompt_language="zh",
            audio_type="wav",
        )
        result = pipeline.predict(query)

        assert isinstance(result, TTSPrediction)
        assert result.wave_data == b"RIFF....wavdata"
        mock_post.assert_called_once()

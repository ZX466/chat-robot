"""Unit tests for pipeline/base/base_sync.py."""
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Tuple

import pytest
from requests import Response
from pydantic import BaseModel

from pipeline.base.base_sync import (
    AbstractPipeline,
    AbstractPipelineConfig,
    AbstractImagePipeline,
    CommonModelPipeline,
    DEFAULT_REQUEST_TIMEOUT,
    PipelineDisabledException,
    PredictablePipeline,
)


# --- Concrete test configs ---

class DummyConfig(AbstractPipelineConfig):
    model_id: str = "test-model"
    predict_url: str = "http://127.0.0.1:9999/predict"
    stream_predict_url: str = "http://127.0.0.1:9999/stream-predict"


class DummyQuery(BaseModel):
    id: str = "test-id"
    text: str = "hello"


class DummyPrediction(BaseModel):
    id: str = "test-id"
    response: str = "world"


# --- Concrete test pipelines ---

class ConcreteCommonPipeline(CommonModelPipeline):
    """Minimal concrete implementation for testing."""

    def __init__(self, config):
        super().__init__(config)

    def parse_prediction(self, response: Response) -> DummyPrediction:
        return DummyPrediction.model_validate_json(response.content)

    def parse_stream_prediction(self, chunk: str) -> DummyPrediction:
        return DummyPrediction.model_validate_json(chunk)


class ConcreteImagePipeline(AbstractImagePipeline):
    """Minimal concrete image pipeline for testing."""

    def __init__(self, config):
        super().__init__(config)

    def parse_prediction(self, response: Response) -> DummyPrediction:
        return DummyPrediction.model_validate_json(response.content)

    def parse_stream_prediction(self, chunk: str) -> DummyPrediction:
        return DummyPrediction.model_validate_json(chunk)


# --- AbstractPipelineConfig ---

@pytest.mark.unit
class TestAbstractPipelineConfig:
    def test_default_enable_is_true(self):
        cfg = AbstractPipelineConfig()
        assert cfg.enable is True

    def test_disable(self):
        cfg = AbstractPipelineConfig(enable=False)
        assert cfg.enable is False


# --- PipelineDisabledException ---

@pytest.mark.unit
class TestPipelineDisabledException:
    def test_is_exception(self):
        assert issubclass(PipelineDisabledException, Exception)

    def test_message(self):
        e = PipelineDisabledException("disabled")
        assert str(e) == "disabled"


# --- AbstractPipeline ---

@pytest.mark.unit
class TestAbstractPipeline:
    def test_none_config_raises(self):
        with pytest.raises(ValueError, match="should not be None"):
            AbstractPipeline(None)

    def test_disabled_config_raises(self):
        cfg = DummyConfig(enable=False)
        with pytest.raises(PipelineDisabledException):
            ConcreteCommonPipeline(cfg)

    def test_enabled_config_ok(self):
        cfg = DummyConfig()
        pipeline = ConcreteCommonPipeline(cfg)
        assert pipeline.model_id == "test-model"


# --- PredictablePipeline ---

@pytest.mark.unit
class TestPredictablePipeline:
    def test_attributes_set(self):
        cfg = DummyConfig()
        pipeline = ConcreteCommonPipeline(cfg)
        assert pipeline.model_id == "test-model"
        assert pipeline.predict_url == "http://127.0.0.1:9999/predict"
        assert pipeline.stream_predict_url == "http://127.0.0.1:9999/stream-predict"
        assert pipeline._timeout == DEFAULT_REQUEST_TIMEOUT


# --- CommonModelPipeline.predict ---

@pytest.mark.unit
class TestCommonModelPipelinePredict:
    @patch("pipeline.base.base_sync.requests.Session")
    def test_predict_posts_json(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_response = MagicMock(spec=Response)
        mock_response.content = DummyPrediction(id="abc", response="ok").model_dump_json().encode()
        mock_response.raise_for_status = MagicMock()
        mock_session.post.return_value = mock_response

        cfg = DummyConfig()
        pipeline = ConcreteCommonPipeline(cfg)
        pipeline._session = mock_session

        query = DummyQuery(id="abc", text="test")
        result = pipeline.predict(query)

        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args
        assert call_kwargs.kwargs["url"] == "http://127.0.0.1:9999/predict"
        assert result.id == "abc"
        assert result.response == "ok"

    @patch("pipeline.base.base_sync.requests.Session")
    def test_predict_raises_on_http_error(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_response = MagicMock(spec=Response)
        mock_response.raise_for_status.side_effect = Exception("500 Internal Server Error")
        mock_session.post.return_value = mock_response

        cfg = DummyConfig()
        pipeline = ConcreteCommonPipeline(cfg)
        pipeline._session = mock_session

        with pytest.raises(Exception, match="500"):
            pipeline.predict(DummyQuery())


# --- CommonModelPipeline.parse_query ---

@pytest.mark.unit
class TestParseQuery:
    def test_parse_pydantic_query(self):
        cfg = DummyConfig()
        pipeline = ConcreteCommonPipeline(cfg)
        query = DummyQuery(id="x", text="hi")
        result = pipeline.parse_query(query)
        assert isinstance(result, dict)
        assert result["id"] == "x"
        assert result["text"] == "hi"

    def test_parse_non_pydantic_raises(self):
        cfg = DummyConfig()
        pipeline = ConcreteCommonPipeline(cfg)
        with pytest.raises(NotImplementedError, match="not a subclass of BaseModel"):
            pipeline.parse_query("not a model")


# --- AbstractImagePipeline ---

@pytest.mark.unit
class TestAbstractImagePipeline:
    def test_predict_with_local_image(self):
        """When img_path is a local file, should use multipart upload."""
        cfg = DummyConfig()
        pipeline = ConcreteImagePipeline(cfg)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            img_path = f.name

        try:
            query = MagicMock()
            query.img_path = img_path
            query.model_dump.return_value = {"id": "test", "img_path": img_path}
            query.model_dump_json.return_value = '{"id": "test", "img_path": "fake"}'

            mock_response = MagicMock(spec=Response)
            mock_response.content = DummyPrediction(id="test", response="ok").model_dump_json().encode()
            mock_response.raise_for_status = MagicMock()
            pipeline._session = MagicMock()
            pipeline._session.post.return_value = mock_response

            result = pipeline.predict(query)
            assert result.id == "test"

            call_kwargs = pipeline._session.post.call_args.kwargs
            assert "files" in call_kwargs
        finally:
            os.unlink(img_path)

    def test_predict_with_remote_image(self):
        """When img_path is not a local file, should use JSON POST."""
        cfg = DummyConfig()
        pipeline = ConcreteImagePipeline(cfg)

        query = MagicMock()
        query.img_path = "http://example.com/image.png"
        query.model_dump.return_value = {"id": "test", "img_path": "http://example.com/image.png"}

        mock_response = MagicMock(spec=Response)
        mock_response.content = DummyPrediction(id="test", response="ok").model_dump_json().encode()
        mock_response.raise_for_status = MagicMock()
        pipeline._session = MagicMock()
        pipeline._session.post.return_value = mock_response

        result = pipeline.predict(query)
        assert result.id == "test"

        call_kwargs = pipeline._session.post.call_args.kwargs
        assert "json" in call_kwargs
        assert "files" not in call_kwargs

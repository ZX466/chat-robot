import pytest

from constants import (
    DEFAULT_HOST,
    MAX_MESSAGE_SIZE_BYTES,
    MAX_UPLOAD_SIZE_BYTES,
    TASK_TIMEOUT_SECONDS,
    MAX_RETRY_COUNT,
    VAD_MODE,
    SAMPLE_RATE,
    QQ_RATE_LIMIT_SECONDS,
)


@pytest.mark.unit
class TestConstants:
    def test_default_host_is_loopback(self):
        assert DEFAULT_HOST == "127.0.0.1"

    def test_max_message_size_is_1mb(self):
        assert MAX_MESSAGE_SIZE_BYTES == 1_048_576

    def test_max_upload_size_is_50mb(self):
        assert MAX_UPLOAD_SIZE_BYTES == 50 * 1024 * 1024

    def test_task_timeout_is_positive(self):
        assert TASK_TIMEOUT_SECONDS > 0

    def test_max_retry_count_is_positive(self):
        assert MAX_RETRY_COUNT > 0

    def test_vad_mode_in_valid_range(self):
        assert 0 <= VAD_MODE <= 3

    def test_sample_rate_is_standard(self):
        assert SAMPLE_RATE in [8000, 16000, 22050, 44100, 48000]

    def test_qq_rate_limit_is_positive(self):
        assert QQ_RATE_LIMIT_SECONDS > 0

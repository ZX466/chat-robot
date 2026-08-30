"""Application-wide constants. Centralizes magic numbers for maintainability."""

# --- Network ---
DEFAULT_HOST = "127.0.0.1"
MAX_MESSAGE_SIZE_BYTES = 1_048_576  # 1MB
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50MB

# --- Task / Timeout ---
TASK_TIMEOUT_SECONDS = 5
MAX_RETRY_COUNT = 3
EVENT_QUEUE_MAXSIZE = 1000

# --- Audio ---
VAD_MODE = 3  # WebRTC VAD aggressiveness (0-3, 3 = most aggressive)
# NOTE: VAD_MODE here is a legacy fallback constant.
# The actual runtime value is configured via SystemConfig.microphone_vad_mode in config.yaml.
SAMPLE_RATE = 16000

# --- QQ Bot ---
QQ_RATE_LIMIT_SECONDS = 2

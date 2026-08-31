# zerolan-vtuber server

虚拟主播服务端：LLM 对话（工具调用）+ 语音识别（ASR）+ 语音合成（TTS），
通过 Zerolan 协议（WebSocket + HTTP）与 Unity 客户端（`zerolan-vtuber/client`）对接。

- **LLM**：litellm 统一入口（任意 OpenAI 兼容端点，含豆包 Ark；Router 降级）
- **ASR/TTS**：自研薄适配（百度 / 火山 BigASR / MiMo），httpx 异步，全局单例连接池
- **工具**：web_search（Tavily 主、ddgs 降级）+ 60s API 工具组（接入中）
- **存储**：SQLite（aiosqlite）仅存聊天历史
- **并发模型**：asyncio 单事件循环，无后台线程

## 目录结构

```
server/
├── app/
│   ├── main.py            # FastAPI 入口与依赖装配
│   ├── config.py          # config.yaml + 环境变量（pydantic-settings）
│   ├── api/               # WS 端点（/ws）与 HTTP 路由
│   ├── protocol/          # Zerolan 协议数据模型（与 Route.cs 对齐）
│   ├── core/              # orchestrator / agent_loop / history / broadcast
│   ├── providers/         # asr(baidu|volcano) / tts(baidu|mimo) / llm / auth
│   └── tools/             # ToolRegistry + web_search
├── tests/                 # pytest + respx 契约测试，样本在 tests/fixtures/
├── config.example.yaml    # 配置示例（复制为 config.yaml）
└── .env.example           # 环境变量示例（复制为 .env）
```

## 快速开始（必须使用 uv）

```bash
cd zerolan-vtuber/server

# 1. 创建虚拟环境并安装依赖（自动生成 .venv）
uv sync

# 2. 填写配置（见下节）
cp config.example.yaml config.yaml   # 按需填写 api_key
cp .env.example .env                 # 环境变量兜底（可选）

# 3. 启动（WS 与 HTTP 同一进程同端口）
uv run uvicorn app.main:app --host 127.0.0.1 --port 8091
```

> 端口说明：服务为单进程 FastAPI，`/ws` 与 HTTP 端点同端口。
> `config.yaml` 中的 `server.ws_port` / `server.http_port` 用于向客户端回显
> `ws_url` / `http_url`（server_hello 与 play_speech 的下载地址），请与实际部署端口保持一致。

## 配置说明

key 优先级：**config.yaml（UI 保存）> 环境变量（.env）**。
`config.yaml` 与 `.env` 均已加入 `.gitignore`，**严禁提交真实密钥**。

| 配置块 | 关键字段 | 说明 |
|---|---|---|
| `llm` | `base_url` / `api_key` / `model` / `fallback_models` | 模型串如 `deepseek/deepseek-chat`、`openai/gpt-4o-mini`、`gemini/gemini-2.0-flash`、`ollama_chat/<model>`、`volcengine/<endpoint-id>`；OpenAI 兼容端点用 `openai/<model>` + `base_url` |
| `asr` | `vendor`(必填 `baidu`\|`volcano`) / `base_url` / `api_key` / `secret_key` / `model` | 百度需 AK/SK 双 key（`secret_key`）；volcano 即火山 BigASR |
| `tts` | `vendor`(必填 `baidu`\|`mimo`) / `base_url` / `api_key` / `secret_key` / `model` / `voice` | 同上，baidu 需 AK/SK |
| `tools.web_search` | `provider`: `tavily`\|`ddgs` | Tavily key 走环境变量 `TAVILY_API_KEY` |
| `tools.sixty_api` | `base_url` | 默认 `https://60s.viki.moe` |
| `server` | `ws_host` / `ws_port` / `http_port` / `audio_dir` | TTS 音频落盘目录默认 `audio_assets/` |
| `broadcast` | `enabled` / `cron`("HH:MM") / `text` | 定时口播（asyncio 调度，跨日可重复） |
| `history` | `db_path` | SQLite 聊天历史，默认 `data/history.db` |

运行中可通过 WS `update_provider_config` 热替换三组 Provider（无需重启，见下文）。

## WebSocket 协议摘要

端点 `ws://{host}:{port}/ws`；消息信封（与 Unity `Route.cs` 完全一致）：

```json
{"protocol": "ZerolanProtocol", "version": "1.1", "message": "...", "action": "...", "code": 0, "data": {...}}
```

服务端支持的行为：

| 客户端发送 | 服务端响应 |
|---|---|
| `client_hello`（data 可携 `session_id`） | `server_hello`：`ws_port`/`res_port`/`ws_url`/`http_url` + 三组 provider 掩码 `{provider, masked}`（key 仅掩码回显，绝不明文）；携带 `session_id` 可复用会话，断线重连历史不丢 |
| 任意 action 携带 `data.text`/`data.content` | 视为用户文本 → orchestrator（LLM+工具）→ 逐句广播 `show_user_text_input`（字幕）与 `play_speech`（data 含 `file_id`、`transcript`、`duration`、`url` 等，URL 指向 HTTP 下载凭据） |
| `update_provider_config`（data: `llm{base_url,api_key,model}`、`asr`/`tts{vendor,base_url,api_key,model}`） | 校验（URL/必填/vendor）→ 热替换 Provider 实例 → 持久化 config.yaml → 回 ack（code=200）；失败回错误 code 与原因；api_key 永不明文回显 |
| `ping` | `pong`（同字面量心跳） |

非法消息 / 未处理 action / 编排失败 → `remote_error`（code 400/500）。

## HTTP 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/playground/microphone` | multipart：`audio`=WAV 文件、`metadata`=JSON `{"Channels":1,"SampleRate":16000}`；→ ASR → 文本编排链路。响应 `{"code":0,"message":"ok","data":{"transcript":"..."}}`（code 0=Success/1=Failed，与 HTTP status 解耦） |
| GET | `/resource/file?file_id={id}` | 下载 `play_speech` 下发的音频（WAV） |
| GET | `/health` | 健康检查 `{"status":"ok"}` |

## 测试与质量

```bash
uv run pytest            # 全量测试（providers 契约测试 + e2e，均 mock 不联网）
uv run ruff check .      # lint
uv run mypy app          # 类型检查（strict）
```

## 安全注意

- `.env` / `config.yaml` / 密钥文件一律不入 git；示例文件仅含占位符。
- `update_provider_config` 的 api_key 只存服务端，日志与 ack 均为掩码。

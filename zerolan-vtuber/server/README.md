# zerolan-vtuber server

虚拟主播服务端:LLM 对话(工具调用)+ 语音识别(ASR)+ 语音合成(TTS),
通过 Zerolan 协议(WebSocket + HTTP)与 Unity 客户端(`zerolan-vtuber/client`)对接。

## 快速部署(5 步)

> 前提:已安装 [uv](https://docs.astral.sh/uv/)(`uv --version` 能出版本号;没有则
> Windows PowerShell: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`)。

```bash
# ① 进入目录
cd zerolan-vtuber/server

# ② 安装依赖(自动创建 .venv)
uv sync

# ③ 建配置文件并填 key
cp config.example.yaml config.yaml     # 然后编辑,至少填 llm.api_key(见下表)
# cp .env.example .env                 # 可选:环境变量兜底

# ④ 启动(WS 与 HTTP 同一进程同端口)
uv run uvicorn app.main:app --host 127.0.0.1 --port 8091

# ⑤ 验证
curl http://127.0.0.1:8091/health      # → {"status":"ok"}
```

看到 `Uvicorn running on http://127.0.0.1:8091` + `/health` 返回 ok 即部署成功。

## 配置(config.yaml)

key 优先级:**config.yaml > 环境变量(.env)**。
两个文件均已加入 `.gitignore`,**严禁提交真实密钥**。

最少只需填一项——`llm.api_key`(DeepSeek 示例):

```yaml
llm:
  api_key: sk-xxxx          # DeepSeek 开放平台申请
  model: deepseek/deepseek-chat
```

| 配置块 | 必填场景 | 关键字段 |
|---|---|---|
| `llm` | **必填** | `api_key`、`model`(如 `deepseek/deepseek-chat`、`openai/gpt-4o-mini`、`gemini/gemini-2.0-flash`);OpenAI 兼容端点用 `openai/<model>` + `base_url` |
| `asr` | 要语音输入才填 | `vendor: baidu` 时填 `api_key` + `secret_key`(百度 AK/SK);`vendor: volcano` 填火山 key |
| `tts` | 要语音播报才填 | `vendor: baidu` 时填 `api_key` + `secret_key`;`vendor: mimo` 填 MiMo key |
| `tools.web_search` | 要联网搜索才填 | `provider: tavily` 时 key 走 `.env` 的 `TAVILY_API_KEY` |
| `server` | 通常不改 | `ws_port: 8090` / `http_port: 8091`,仅用于向客户端回显地址,与启动端口保持一致 |
| `broadcast` / `history` | 可选 | 定时口播 / SQLite 路径(默认 `data/history.db`) |

> 没填 ASR/TTS 也能启动;客户端连上后可在"模型服务"界面运行中热填
> (WS `update_provider_config`,仅内存生效,api_key 掩码回显,详见下文)。

## 客户端怎么连

1. 启动 Unity 打包的 exe(见 `../client/README.md` 打包步骤)
2. 客户端"设置"里填服务器地址 `ws://127.0.0.1:8091/ws` → 连接
3. 连接成功:`client_hello` → `server_hello`(回显三组供应商掩码,如 `deepseek/d***`)
4. 对话:客户端发文本 → 服务端 LLM+工具 → 逐句回 `show_user_text_input`(字幕)+ `play_speech`(TTS 音频下载地址)

## Live2D 模型下发(换模型零打包)

服务端可向客户端下发 Live2D 人物模型——**换模型只需替换服务端文件,不用重新打包 exe**:

```bash
# ① 放模型:zip 内含 <名字>.model3.json(官方示例 Rice 已内置)
zerolan-vtuber/models/rice.zip

# ② 改配置:config.yaml
server:
  live2d_model: rice        # 模型名 = zip 文件名(不含 .zip);留空/删行 = 不下发

# ③ 重启 server → 客户端连上后自动下载并加载模型
```

zip 要求:根目录(或一级子目录)含 `*.model3.json` + `.moc3` + 贴图;动作放 `motions/`。
内置 `models/Rice/` 为 Live2D Cubism 官方免费示例(示例许可),可直接改名替换。

## 协议摘要

端点 `ws://{host}:{port}/ws`;信封与 Unity `Route.cs` 完全一致:

```json
{"protocol": "ZerolanProtocol", "version": "1.1", "message": "...", "action": "...", "code": 0, "data": {}}
```

| 客户端发送 | 服务端响应 |
|---|---|
| `client_hello` | `server_hello`(端口/URL 回显 + provider 掩码;配置了 `live2d_model` 时附 `live2d_model.model_file_id` 触发客户端加载模型;`data.session_id` 可复用会话,重连历史不丢) |
| 携带 `data.text` 的消息 | 用户文本 → LLM 编排 → 字幕 + `play_speech` |
| `update_provider_config` | 校验 → 热替换(填哪槽换哪槽,llm/asr/tts 可选)→ ack;失败回 400+原因;仅内存生效,不写 config.yaml |
| `ping` | `pong` |

非法消息/编排失败 → `remote_error`(code 400/500)。

## HTTP 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/playground/microphone` | multipart:`audio`=WAV + `metadata`=`{"Channels":1,"SampleRate":16000}` → ASR → 编排 |
| GET | `/resource/file?file_id={id}` | 下载 `play_speech` 下发的音频;`file_id=model:<名字>` 下载 Live2D 模型 zip |
| GET | `/resource/file?file_id=model:{name}` | Live2D 模型包(`models/{name}.zip`) |

## 测试与质量

```bash
uv run pytest                                    # 全量测试(mock 不联网,当前 76 用例)
uv run pytest --cov=app --cov-fail-under=80      # 覆盖率门禁 ≥80%(当前 86%)
uv run ruff check .                              # lint
uv run mypy app                                  # 类型检查(strict)
```

## 安全注意

- `.env` / `config.yaml` 一律不入 git;示例文件仅含占位符。
- `update_provider_config` 的 api_key 只存服务端,日志与 ack 均为掩码,绝不明文回显。

## 目录结构

```
server/
├── app/
│   ├── main.py            # FastAPI 入口与依赖装配
│   ├── config.py          # config.yaml + 环境变量(pydantic-settings)
│   ├── api/               # WS 端点(/ws)与 HTTP 路由
│   ├── protocol/          # Zerolan 协议数据模型(与 Route.cs 对齐)
│   ├── core/              # orchestrator / agent_loop / history / broadcast
│   ├── providers/         # asr(baidu|volcano) / tts(baidu|mimo) / llm / auth
│   └── tools/             # ToolRegistry + web_search + sixty_api
├── models/                # Live2D 模型 zip(live2d_model 下发;Rice 为官方示例)
├── tests/                 # pytest + respx 契约测试
├── config.example.yaml    # 复制为 config.yaml
└── .env.example           # 复制为 .env(可选)
```

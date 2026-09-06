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
| `llm` | **必填** | `api_key`、`model`(如 `deepseek/deepseek-chat`、`openai/gpt-4o-mini`);**OpenRouter** 用 litellm 原生前缀 `openrouter/<org>/<model>:free`(无需 base_url) |
| `asr` | 要语音输入才填 | `vendor: baidu` 填 `api_key` + `secret_key`(百度 AK/SK);`vendor: volcano` 填火山 key;`vendor: openai` 填任意 OpenAI 兼容 `/v1/audio/transcriptions` 端点(base_url/api_key/model) |
| `tts` | 要语音播报才填 | `vendor: baidu` 填 `api_key` + `secret_key`;`vendor: mimo` 填 MiMo key;`vendor: openai` 填任意 OpenAI 兼容 `/v1/audio/speech` 端点(base_url/api_key/model/voice);**voice 只在 config.yaml 配**(面板 4 字段不含它,热替换自动沿用当前音色) |
| `tools.web_search` | 要联网搜索才填 | `provider: tavily` 时 key 走 `.env` 的 `TAVILY_API_KEY` |
| `server` | 通常不改 | `ws_port: 8090` / `http_port: 8091`,仅用于向客户端回显地址,与启动端口保持一致 |
| `broadcast` / `history` | 可选 | 定时口播 / SQLite 路径(默认 `data/history.db`) |

## 实测配方(2026-09-05):ASR=siliconflow · LLM/TTS=OpenRouter 免费

```yaml
llm:
  api_key: null          # ← .env 里 OPENROUTER_API_KEY / LLM__API_KEY(sk-or-v1-…)
  model: openrouter/deepseek/deepseek-chat-v3-0324:free
asr:
  vendor: openai
  base_url: https://api.siliconflow.cn
  api_key: null          # ← siliconflow key(sk-…)
  model: FunAudioLLM/SenseVoiceSmall   # 免费中文转写;备选 TeleAI/TeleSpeechASR
tts:
  vendor: openai
  base_url: https://openrouter.ai/api   # 注意:拼 /v1/audio/speech,别只填 openrouter.ai
  api_key: null          # ← OpenRouter key(与 llm 同一把)
  model: deepgram/flux-tts:free
  voice: flux-alexis-en  # flux 系 36 音色全英文(flux-bree/hannah/marcus/…);中文自然语音换 siliconflow fish-speech
```

对应 `.env`(在 `zerolan-vtuber/` 下即 PROJECT_DIR,不在 server/ 下;字段名 `槽位__字段`):

```
LLM__API_KEY=sk-or-v1-…
ASR__API_KEY=sk-…
TTS__API_KEY=sk-or-v1-…   # 与 LLM 同一把 OpenRouter key
```

> 客户端设置面板可随时热替换 vendor/base_url/api_key/model(项目特色,详见
> "客户端怎么连");voice 是唯一不在面板上的字段——改音色编辑 config.yaml 后重启。

> 没填 ASR/TTS 也能启动;客户端连上后可在"模型服务"界面运行中热填
> (WS `update_provider_config`,仅内存生效,api_key 掩码回显,详见下文)。

## 配置模型详细步骤(含常见填法与报错对照)

### 第 0 步:理解 model 前缀(最重要的一个坑)

`model` 字段**不是裸模型名**,开头的前缀告诉 litellm 用哪家的协议:

| 供应商形态 | model 怎么填 | base_url | 实例 |
|---|---|---|---|
| OpenAI 兼容自定义端点(微信/豆包 Ark/siliconflow/中转站/自建 vLLM…) | **`openai/<模型名>`**(前缀必须加) | 填到 `/v1` 截断(**不含** `/chat/completions` 等路径) | `openai/Deepseek-v4-flash` + `https://chatapi.weixin.qq.com/openai/v1` |
| OpenRouter | `openrouter/<org>/<model>`(免费模型带 `:free`) | 不填 | `openrouter/deepseek/deepseek-chat-v3-0324:free` |
| DeepSeek 官方 | `deepseek/deepseek-chat` | 不填 | |
| OpenAI 官方 | `openai/gpt-4o-mini` | 不填(走官方默认) | |

> 裸模型名(如 `Deepseek-v4-flash`)会报
> `litellm.BadRequestError: LLM Provider NOT provided` —— 补前缀即解决。

### 第 1 步:server 侧启动配置(config.yaml)

编辑 `server/config.yaml`(此文件不入 git),按下方模板填;key 也可以放 `.env`:

```yaml
llm:
  base_url: null                      # OpenRouter 不填;自定义端点填到 /v1
  api_key: null                       # 或 .env 里 LLM__API_KEY
  model: openrouter/deepseek/deepseek-chat-v3-0324:free
asr:                                  # 语音识别(不要填 TTS 模型!)
  vendor: openai
  base_url: https://api.siliconflow.cn
  api_key: null                       # 或 .env 里 ASR__API_KEY
  model: FunAudioLLM/SenseVoiceSmall
tts:                                  # 语音合成(不要填 ASR 模型!)
  vendor: openai
  base_url: https://openrouter.ai/api
  api_key: null                       # 或 .env 里 TTS__API_KEY
  model: deepgram/flux-tts:free
  voice: flux-alexis-en               # 唯一不在面板上的字段,见第 3 步
```

`.env` 写法(文件放 **`zerolan-vtuber/`** 下,即 PROJECT_DIR,不在 server/ 下;
字段名 = `槽位大写__字段大写`):

```
LLM__API_KEY=sk-or-v1-你的OpenRouter钥匙
ASR__API_KEY=sk-你的siliconflow钥匙
TTS__API_KEY=sk-or-v1-与LLM同把OpenRouter钥匙
```

启动:`uv run uvicorn app.main:app --host 127.0.0.1 --port 8091`

### 第 2 步:客户端面板热替换(不重启换供应商,项目特色)

exe 连上 server 后,设置面板每槽填 4 个字段 → 点"应用配置"→ **即时生效**:

| 槽位 | 4 字段 | 填法示例(换成某 OpenAI 兼容端点) |
|---|---|---|
| LLM | Base URL / API Key / Model | `https://chatapi.weixin.qq.com/openai/v1` / 微信key / `openai/Deepseek-v4-flash` |
| ASR | Vendor / Base URL / API Key / Model | `openai` / `https://api.siliconflow.cn` / siliconflowkey / `FunAudioLLM/SenseVoiceSmall` |
| TTS | Vendor / Base URL / API Key / Model | `openai` / `https://openrouter.ai/api` / OpenRouterkey / `deepgram/flux-tts:free` |

规则:
- **vendor 填 `openai`** 即走 OpenAI 兼容实现(覆盖市面上绝大多数 ASR/TTS/LLM 端点);
  填 `baidu`/`volcano`/`mimo` 走对应专用实现;其他值回 400 并列支持的清单。
- **key 只发服务端内存**,不落盘、日志掩码;重启后回到 config.yaml 的配置。
- **base_url 截到 `/v1`**,别带 `/chat/completions`、`/audio/speech` 等尾部路径
  (各功能路径由服务端按功能自动拼接)。
- 热替换**沿用当前音色**(voice):换供应商/模型不会把音色冲掉。

### 第 3 步:改音色(voice)

voice 只在 `config.yaml` 的 `tts.voice` 配置(面板没有此字段),改完重启 server 生效:

```yaml
tts:
  voice: flux-alexis-en    # deepgram flux 系:36 个全英文音色
                           # (flux-bree/hannah/marcus/miles/…,报错信息里列全)
```

> flux 系是英文音色,念中文会带口音;要自然的中文语音,把 TTS 槽整个换到
> siliconflow 的 fish-speech:`base_url: https://api.siliconflow.cn`、
> `model: fishaudio/fish-speech-1.5`、`voice: <fish 音色名>`,key 用 siliconflow 那把。

### 常见报错速查

| 报错(关键词) | 原因 | 解决 |
|---|---|---|
| `LLM Provider NOT provided` | model 缺前缀 | 加 `openai/` 或对应前缀(见第 0 步表) |
| `Model xxx does not exist, 400` | ASR/TTS 槽填错模型(如把 TTS 填进 ASR);或模型名少 `:free` 后缀 | 按槽位功能选模型;OpenRouter 免费模型名必须带 `:free` |
| `Unknown voice "alloy"` | TTS 音色不被该供应商支持 | config.yaml 改 `tts.voice` 为该供应商支持的音色 |
| `asr.vendor must be…` / `unsupported vendor` | vendor 拼错或为空 | 填 `openai`(通用)或 baidu/volcano/mimo |
| 麦克风说话后无反应,server 日志 404 | 老版本 `/resource/file` 硬编码 .wav | 升级到 b59598d+ |
| 面板提交后音色失效 | 老版本热替换把 voice 冲回默认 | 升级到 29cc863+ |

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
uv run pytest                                    # 全量测试(mock 不联网,当前 108 用例)
uv run pytest --cov=app --cov-fail-under=80      # 覆盖率门禁 ≥80%
uv run ruff check .                              # lint
uv run mypy app                                  # 类型检查(strict,32 files)
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
│   ├── providers/         # asr(baidu|volcano|openai) / tts(baidu|mimo|openai) / llm / auth
│   └── tools/             # ToolRegistry + web_search + sixty_api
├── models/                # Live2D 模型 zip(live2d_model 下发;Rice 为官方示例)
├── tests/                 # pytest + respx 契约测试
├── config.example.yaml    # 复制为 config.yaml
└── .env.example           # 复制为 .env(可选)
```

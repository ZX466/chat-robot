# zerolan-vtuber 合并重构 · Claude Code 任务提示词（终版）

> **用途**：本文件是投喂给专属 Claude Code 的完整任务说明。在新的 Claude Code 会话中将本文件全文作为初始任务输入执行。
> **版本**：2026-08-30 终版（LiteLLM 方案 + Unity 配置界面方案 A）。与旧代码冲突时以本文件为准。

---

# 任务：构建 zerolan-vtuber 合并版服务端（LiteLLM 方案）

你是一名资深 Python 后端工程师。请基于以下完整规格，在现有仓库中实施重构。

## 1. 项目背景（现状，已完成调研，勿重复探索结论性内容）

当前仓库 e:\zxdevelop\project3 是一个 5 子项目虚拟主播系统，本次任务将其合并为单项目：

- **ZerolanLiveRobot/**（Python 主控）：保留其**云端 API 管线**代码作为迁移素材：
  - `pipeline/llm/doubao_ark_llm.py`（豆包 Ark，requests 同步）
  - `pipeline/tts/baidu_tts.py`、`pipeline/tts/mimo_tts.py`
  - `pipeline/asr/baidu_asr.py`、`pipeline/asr/bigasr_asr.py`
  - `pipeline/utils/baidu_auth.py`（百度 access_token 获取流程，需改为异步 + 过期刷新）
- **ZerolanPlayground/**（Unity C# 客户端）：仓库中仅含 `Assets/Scripts` 代码（无
  ProjectSettings/Packages），并入使用者本机 Unity 工程模板即可。**协议层必须兼容**：
  - `Assets/Scripts/Data/Route.cs` 中 action 常量：client_hello / server_hello /
    play_speech / show_user_text_input / add_history / show_menu / load_live2d_model
  - `Assets/Scripts/Web/ZerolanProtocolClient.cs`：含心跳、指数退避重连、
    按 action 注册回调；消息为 JSON `{protocol, version, message, action, code, data}`
  - `Assets/Scripts/Handlers/SpeechHandler.cs` 通过 HTTP URL 下载音频（GetAudioClipAsync）
  - `Assets/Scripts/Controller/UI/ConfigController.cs` 已实现"输入→解析→保存"配置模式，
    是本任务客户端配置 UI 的复用模板
  - `Assets/Scripts/Controller/MicrophoneController.cs` + `Web/Api/HttpApi.cs`：
    语音上传机制**已存在**——麦克风开关按钮（16kHz）关闭时将 WAV 经 multipart
    POST 到 `http://{http服务}/playground/microphone`（part "audio"=WAV 文件，
    part "metadata"=JSON{Channels,SampleRate}），响应按 `HttpResponseBody{code,message}`
    风格解析
- **整体删除**（不迁移、不保留兼容层）：zerolan-core/（Flask+本地 GPU 推理）、
  KonekoMinecraftBot/、直播弹幕服务、OBS、浏览器服务、设备层
  （microphone/keyboard/screen/speaker，录音改由客户端负责）、Milvus 向量库。

## 2. 目标产物

单仓库新项目 `zerolan-vtuber/`，只含两个应用：server/（Python，本次全部工作）
与 client/（原样迁入 ZerolanPlayground，仅允许白名单最小 diff，见第 12 节）。

**运行形态**（两个程序）：

```
┌─ 电脑 A（可无 GPU，全云端 API）──────┐    ┌─ 电脑 B / 同一台机 ────────┐
│ python server（FastAPI）             │◄──►│ ZerolanPlayground.exe      │
│ config.yaml（供应商配置、api_key）   │ WS │ Unity 打包产物：展示+录音  │
└──────────────────────────────────────┘    │ + 供应商配置界面（第12节） │
                                            └────────────────────────────┘
```

目录结构：

```
zerolan-vtuber/
├── server/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口，挂载 WS 与 HTTP 路由
│   │   ├── api/
│   │   │   ├── ws.py            # WebSocket：Playground 协议端点
│   │   │   ├── http.py          # HTTP：/playground/microphone 语音上传、/audio/{id}、/health
│   │   ├── core/
│   │   │   ├── orchestrator.py  # ConversationPipeline：ASR→LLM(带工具)→TTS 编排
│   │   │   ├── agent_loop.py    # 工具调用循环（最多 3 轮）
│   │   │   └── history.py       # 会话历史（内存 + SQLite 落盘）
│   │   ├── providers/
│   │   │   ├── llm.py           # LiteLLM 封装（唯一 LLM 入口）
│   │   │   ├── asr.py           # ASRProvider Protocol + baidu/volcano(bigasr) 实现
│   │   │   └── tts.py           # TTSProvider Protocol + baidu/mimo 实现
│   │   ├── tools/
│   │   │   ├── registry.py      # ToolRegistry：JSON Schema 生成 + 分发
│   │   │   ├── web_search.py    # SearchProvider：tavily 默认，ddgs 兜底
│   │   │   └── sixty_api.py     # 60s API 客户端（见第 6 节）
│   │   ├── protocol/models.py   # pydantic v2 模型（从 zerolan-data 精简并入）
│   │   └── config.py            # pydantic-settings，YAML+环境变量
│   ├── tests/
│   ├── pyproject.toml           # uv 管理
│   └── .env.example
├── client/                      # 移入的 Unity 工程，白名单最小 diff（第 12 节）
└── .github/workflows/ci.yml     # ruff + mypy + pytest
```

## 3. 技术栈（硬性规定，不得更换）

- Python 3.12+，包管理用 uv，单 pyproject.toml
- Web：FastAPI + uvicorn（单 asyncio 事件循环；除音频写盘外禁止任何后台线程）
- LLM：litellm（统一 100+ 供应商、统一 tool calling 与流式；Router 做降级重试）
- HTTP 客户端：httpx.AsyncClient（全局单例连接池；禁止 requests）
- 数据校验：pydantic v2 + pydantic-settings
- 日志：loguru
- 定时任务：asyncio 原生循环（不引入 APScheduler）
- 存储：SQLite（aiosqlite）仅存聊天历史；禁止向量库/ORM
- 测试：pytest + pytest-asyncio + respx（mock httpx）；类型 mypy strict
- Lint：ruff；CI：GitHub Actions（lint + typecheck + test 三道闸）

## 4. Provider 层规格

### 4.1 LLM（LiteLLM）

- 唯一入口 `LLMProvider.acompletion(messages, tools=None) -> LLMResponse` 与
  `stream_completion(...) -> AsyncIterator[delta]`，内部调 `litellm.acompletion`。
- 模型串规则写入 config：
  - `deepseek/deepseek-chat`、`openai/gpt-4o-mini`、`gemini/gemini-2.0-flash`、
    `ollama_chat/<model>`
  - 豆包（火山方舟）：litellm 原生前缀 `volcengine/<endpoint-id>`，
    环境变量 `VOLCENGINE_API_KEY` 或 `ARK_API_KEY`
  - **任意 OpenAI 兼容端点**（含豆包 Ark base_url `https://ark.cn-beijing.volces.com/api/v3`）：
    `openai/<model>` + 调用时 `api_base` / `api_key` 覆盖——
    **这正是第 12 节 Unity 前端三元组（base_url/api_key/model）的映射点**
- API key 来源优先级：config.yaml（UI 保存的）> 环境变量；禁止明文密钥进 git。
- 配置 fallback 模型列表，用 litellm.Router 实现（主模型失败自动降级）。
- 流式输出必须支持 tool_call 增量片段聚合（litellm 已统一格式，实现聚合器）。
- **运行时热替换**：收到 update_provider_config 后，用新三元组重建对应
  Provider 调用参数（无需重启，见第 7 节）。

### 4.2 ASR / TTS（自研薄适配，litellm 不覆盖中文云厂商）

- 定义 Protocol：

```python
class ASRProvider(Protocol):
    async def transcribe(self, audio: bytes, fmt: str) -> str: ...

class TTSProvider(Protocol):
    async def synthesize(self, text: str, voice: str) -> AsyncIterator[bytes]: ...  # 音频块流式
```

- 迁移现有 baidu_asr / bigasr_asr / baidu_tts / mimo_tts 到上述接口，
  requests→httpx，baidu_auth 的 token 获取改为异步并带过期刷新。
- 每家一个类，禁止用"万能通用类"适配所有厂商差异。
- 每个实现配 respx 契约测试（真实响应样本放 tests/fixtures/）。
- **ASR/TTS 与 LLM 同等支持前端自定义供应商**：每个槽位可配置
  `{vendor, base_url, api_key, model}`。vendor 决定请求协议实现——注意 ASR/TTS
  无统一协议标准（与 LLM 的 OpenAI 兼容事实标准不同），故 vendor 为必填选择项，
  三元组是该 vendor 实现的参数。vendor 取值按槽位：
  ASR=baidu/volcano（bigasr 即火山 BigASR）；TTS=baidu/mimo。
  运行中通过 update_provider_config 热替换实例，行为与 LLM 一致（见第 7 节）。

## 5. Agent 工具循环（web search + 60s API 都走这里）

- ToolRegistry：每个 Tool = {name, description, parameters(JSON Schema), handler}。
  用 pydantic 模型自动生成 JSON Schema，直接传给 litellm 的 tools 参数。
- agent_loop 最多 3 轮工具调用；单工具执行超时 10s；工具结果注入前截断至
  2000 字符；全程结构化日志记录每轮 tool_call。
- 内置工具：
  1. `web_search(query, max_results=5)` → SearchProvider；
     Tavily 为主（env: TAVILY_API_KEY），失败自动降级 ddgs。
     返回 `[{title, url, snippet}]`，要求 LLM 回答时口播引用来源域名。
  2. 60s API 工具组（见第 6 节）。
- 工具仅由 LLM 自主决定调用，不做关键词硬编码分发（废弃旧 asr_dispatch 模式）。

## 6. 60s API 客户端（tools/sixty_api.py）

- BaseURL 可配置，默认 `https://60s.viki.moe`，支持自托管（Docker 4399）。
- 统一响应包 `{code:200, message, data}`；code!=200 抛 SixtyApiError。
- httpx + 内存 TTL 缓存（热榜类 600s，资讯类 1800s，天气 600s）。
- 封装为独立 Tool 注册：

| 工具名 | 端点 | 说明 |
|---|---|---|
| get_daily_news | /v2/60s?encoding=markdown | 每日60秒读世界（markdown 为 AI 优化格式） |
| get_hot_list(platform) | /v2/{bili,weibo,zhihu,douyin,toutiao,xiaohongshu} | 各平台实时热搜 |
| get_weather(city) | /v2/weather | 实时天气 |
| get_epic_free | /v2/epic | Epic 免费游戏 |
| get_exchange_rate | /v2/exchange-rate | 汇率 |
| get_hitokoto | /v2/hitokoto | 一言 |
| get_moyu | /v2/moyu | 摸鱼日报 |

- 端点路径以 60s API 官方文档（docs.60s-api.viki.moe）为准，实施时逐一核对。
- 另提供"主动播报"能力：asyncio 后台定时任务（可配置开关与 cron 时分），
  触发时拉取 get_daily_news 或 get_moyu → LLM 按人设改写成口播稿 →
  TTS → 走与对话相同的 WS 输出通道播放；服务重启后下次触发自动恢复。

## 7. 与 Unity 客户端的 WS 协议（兼容性验收红线）

- 端点 `ws://{host}:{port}/ws`；消息 JSON 结构
  `{protocol:"ZerolanProtocol", version, message, action, code, data}`。
- 必须实现的服务端行为：
  - 收 client_hello → 回 server_hello（data 含 ws/http 服务地址，
    以及 llm/asr/tts 三组槽位各自的 provider 掩码（如 `deepseek/k***`）供客户端回显）
  - 收 HTTP POST /playground/microphone（multipart："audio"=WAV 文件，
    "metadata"=JSON{Channels,SampleRate}；客户端 16kHz、开关按钮触发、单段最长 10s）
    → ASR → 文本进入与文本输入相同的编排链路（字幕/历史经 WS 下发）；
    响应体沿用客户端已解析的 HttpResponseBody{code,message} 风格，
    metadata 字段按现有 AudioMetadata 序列化大小写（Channels/SampleRate）用别名兼容
  - 文本经 orchestrator（LLM+工具）→ 逐句：
    a) 发 show_user_text_input / add_history（字幕与聊天记录）
    b) TTS 音频落临时文件，发 play_speech（data 含 `{url:"http://…/audio/{id}", …}`）
  - 收 update_provider_config（data 含三组配置：
    llm=`{base_url, api_key, model}`；asr/tts=`{vendor, base_url, api_key, model}`）
    → 校验（URL 合法、必填非空、vendor 合法）→ 热替换对应 Provider 实例（无需重启）
    → 持久化到 config.yaml（.gitignore 排除）→ 回 ack（code=200）；
    校验失败回错误 code 与原因；api_key 永不在任何日志与 ack 回显明文。
  - 心跳 ping/pong 与断线重连期间状态保持（会话历史不丢）。
- version 字段照抄 Route.cs 现有常量，不得变更现有 action 语义，只允许新增
  update_provider_config。

## 8. 配置（config.py）

单一 config.yaml + 环境变量覆盖（pydantic-settings），结构：

```
llm(base_url, api_key, model, fallback_models, temperature)
asr(vendor, base_url, api_key, model)
tts(vendor, base_url, api_key, model, voice)
tools(web_search.provider, sixty_api.base_url)
server(ws_host=127.0.0.1, ws_port, http_port)
broadcast(播报定时任务开关)
history(db_path)
```

- key 来源优先级：config.yaml（UI 保存）> 环境变量（headless/CI 场景）。
- 安全要求：.env 与真实 config.yaml 进 .gitignore；.env.example 与
  config.example.yaml 只含占位符。

## 9. 实施顺序（每步可独立提交，Conventional Commits）

1. chore: git init、目录骨架、uv 初始化、CI workflow
2. feat(protocol): 从 zerolan-data 精简并入 pydantic 模型（protocol/llm/asr/tts）
3. feat(providers): LLMProvider（LiteLLM+Router+流式 tool_call 聚合）与契约测试
4. feat(providers): ASR/TTS 迁移（httpx 异步化）
5. feat(tools): ToolRegistry + agent_loop + web_search
6. feat(tools): sixty_api 客户端 + 7 个工具 + TTL 缓存 + 契约测试
7. feat(core): orchestrator + history(SQLite)
8. feat(api): WS 端点（第 7 节全部行为）+ HTTP 端点（/playground/microphone 语音上传、/audio/{id}、/health）
9. feat(broadcast): asyncio 定时播报任务
10. feat(client): Unity 配置界面最小 diff（第 12 节白名单）
11. docs: server/README.md（启动方式、配置说明、与 Unity 联调步骤）

## 10. 验收标准（全部满足才算完成）

- [ ] 在 server/ 目录下 `uv run ruff check .`、`uv run mypy app`、`uv run pytest`
      全绿，覆盖率 ≥80%（providers/tools/core 为主要覆盖对象）
- [ ] 全链路单元级 E2E：mock ASR/LLM/TTS 后，"文本进→分句→play_speech
      协议消息出"可在测试中断言；语音路径同样断言：multipart POST
      /playground/microphone（WAV 样本）→ play_speech 出
- [ ] 60s API 工具真实调用冒烟通过（CI 中 skip，本地手动验证）
- [ ] client/ 改动仅限第 12 节白名单文件，diff 最小化；全仓库无明文 API key
- [ ] 热替换测试：运行中发送 update_provider_config 后，下一次对话使用新
      供应商（mock 验证）
- [ ] 仅用 asyncio；无 requests/torch/transformers/milvus 依赖残留
- [ ] litellm Router 降级路径有测试

## 11. 明确禁止

- 禁止引入 RAG/向量库、直播弹幕、OBS、浏览器控制、设备采集
- 禁止为"未来可能的供应商"做抽象预留（只在三家内保持接口最小化）
- 禁止修改 ZerolanPlayground 除第 12 节白名单外的任何文件；现有 action 字段
  语义不得变更，只允许新增 update_provider_config
- 禁止在 import 时产生 IO 副作用（旧 bot.py 的 get_config() 模式是反面教材）
- 禁止创建本文件与 server/README.md 之外的新文档

## 12. 客户端白名单最小 diff（供应商配置 UI）

允许改动且**仅允许**以下文件：

1. `Assets/Scripts/Data/Route.cs` —— 新增常量 `update_provider_config`
2. `Assets/Scripts/Controller/UI/ConfigController.cs` —— 复用其现有
   "输入→解析→保存"模式，新增"模型服务"分区：
   LLM 3 个输入框（base_url / api_key / model）；
   ASR 下拉框（baidu/volcano）、TTS 下拉框（baidu/mimo）各 1 个 + 3 个输入框
   （base_url / api_key / model）；+ 保存按钮；
   api_key 输入框用 ContentType.Password
3. `Assets/Scripts/Handlers/ProviderConfigHandler.cs`（新增）—— 按现有 Handler
   模式（[Handler]+[OnProtocolReceived]）实现 ack 处理与 Toast 反馈
4. 对应 UI Prefab 增加输入框节点（场景侧最小改动）

约束：

- 配置不落盘在客户端（api_key 只存服务端 config.yaml）；客户端重连后通过
  server_hello 附带的 provider 掩码状态（如 `deepseek/k***`）回显
- 服务端收到 update_provider_config 后热替换 Provider 实例（providers 注册表
  重新初始化对应槽位），全程无重启
- 必须沿用 ZerolanProtocolClient 现有发送/心跳/重连机制，不得新写网络代码

---

## 附：技术栈终审记录（2026-08-30，供追溯）

| 项 | 结论 | 依据 |
|---|---|---|
| Python 3.12+/uv | 保留 | 单文件依赖管理，替代旧仓库 7 份混用 lock |
| FastAPI+uvicorn | 保留 | async+WS+Pydantic 原生集成，替代 Flask |
| litellm | 保留 | 已核实 volcengine/ 原生前缀 + 任意 OpenAI 兼容端点 api_base 覆盖，与前端三元组配置直接映射；Router 提供降级 |
| httpx/pydantic v2/loguru/aiosqlite | 保留 | 无争议 |
| APScheduler | 移除 | 仅 1 个播报定时任务，asyncio 原生循环足够，少一依赖 |
| pytest+respx+ruff+mypy | 保留 | CI 三道闸 |
| Unity 2022 LTS/UniTask/自研 WS 栈/Live2D+DOTween | 全部保留 | 自研 WS 已含心跳+指数退避+按 action 分发，替换为纯重写风险零收益；口型一期音量包络、二期可评估 uLipSync 或带 viseme 的 TTS |
| Unity 配置界面（方案 A） | 新增 | 用户选定：复用 ConfigController 模式 + 1 个新 action，约 3 文件最小 diff，key 只存服务端 |

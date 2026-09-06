# zerolan-vtuber

云端 API 虚拟主播系统：Python 服务端 + Unity Live2D 桌宠客户端，文字/语音对话、表情动作、供应商运行中热替换，无需 GPU。

## 功能

**对话与语音**
- 文字/麦克风语音对话（ASR→LLM→TTS 云端管线，字幕 + 双侧聊天气泡 + 语音播报）
- 多会话记忆：session_id 隔离，SQLite 落盘，断线重连不丢历史
- "识别中…"反馈、逐句分句播报、音色（voice）面板/配置双路设定
- 定时播报：cron 触发，LLM 按人设改写口播稿后 TTS 播出

**供应商与配置**
- LLM：litellm 统一入口（deepseek/openai/gemini/ollama/任意 OpenAI 兼容端点），Router 主模型失败自动降级，流式 tool_call 聚合
- ASR/TTS：baidu/volcano/mimo + 任意 OpenAI 兼容端点（如 siliconflow），百度 token 异步刷新
- 热替换：客户端面板"模型服务"运行中改供应商（base_url/api_key/model），key 只存服务端，重连回显掩码（`deepseek/d***`）

**Agent 工具（LLM 自主调用，最多 3 轮）**
- `web_search`：Tavily 主，失败降级 ddgs，要求口播引用来源
- 60s API 工具组：每日新闻 / 各平台热搜 / 天气 / Epic 免费 / 汇率 / 一言 / 摸鱼日报——TTL 缓存（资讯 1800s / 热榜天气 600s）、统一响应包校验、结果截断 2000 字符；机制详见 server/README.md

**客户端（Unity 2022.3）**
- Live2D 人物渲染（口型/眨眼/视线/呼吸），服务端配置模型 zip 下发，换模型零重新打包（放 zip → 改一行配置 → 重启，见 server/README.md）
- 桌宠透明窗口模式、设置面板、Toast 提示
- 麦克风 16kHz 录音 multipart 上传

## 快速开始

```bash
# ① 服务端
cd zerolan-vtuber/server
uv sync
cp config.example.yaml config.yaml    # 填 LLM/ASR/TTS 的 api_key
uv run uvicorn app.main:app --host 127.0.0.1 --port 8091

# ② 客户端
# 运行 zerolan-vtuber.exe → 齿轮设置 → ws://127.0.0.1:8091/ws → 连接 → 对话
```

WS `:8090/ws` 协议端点（字幕/气泡/语音/热替换）；HTTP `:8091`（`/playground/microphone` 语音上传、`/resource/file` 文件下载、`/health`）。

## 质量与 CI

`uv run ruff check .` + `uv run mypy app`（strict）+ `uv run pytest`（117 passed / 覆盖 86%），push/PR 自动跑（GitHub Actions）。

## 文档

- [server/README.md](zerolan-vtuber/server/README.md) — 部署、config.yaml 逐项说明、免费供应商配方、报错速查、协议摘要
- [client/README.md](zerolan-vtuber/client/README.md) — 打包（团结云云构建/本地 Unity）、首次运行配置、已知边界

# zerolan-vtuber

单仓库虚拟主播系统：云端 API 管线服务端（Python）+ Unity 桌宠客户端，Live2D 人物渲染、语音对话（ASR→LLM→TTS）、聊天记录、供应商热替换。

```
zerolan-vtuber/
├── server/    # Python 3.12 + uv + FastAPI + litellm（部署与配置见 server/README.md）
├── client/    # Unity 2022.3 桌宠客户端（打包与运行见 client/README.md）
└── .github/workflows/ci.yml  # CI：ruff + mypy + pytest
```

## 快速开始（3 步）

1. **启动服务端**（无需 GPU，全云端 API）：

   ```bash
   cd zerolan-vtuber/server
   uv sync
   cp config.example.yaml config.yaml   # 填入 LLM/ASR/TTS 的 api_key
   uv run uvicorn app.main:app --host 127.0.0.1 --port 8091
   ```

   详细配置（model 前缀规则、免费供应商配方、报错对照）见 **server/README.md**。

2. **运行客户端**：下载云构建产物（或本地 Unity 打包，见 client/README.md）运行
   `zerolan-vtuber.exe` → 齿轮设置 → 填 `ws://127.0.0.1:8091/ws` → 连接。

3. **对话**：文字输入或开麦克风说话 → 字幕 + 聊天气泡 + 语音播报。
   面板"模型服务"可运行中热替换供应商，无需重启。

## 通信架构

- **WS** `ws://{host}:8090/ws`（协议端点）：client_hello/server_hello、字幕、聊天记录、play_speech 语音下发、update_provider_config 热替换。协议摘要见 server/README.md。
- **HTTP** `http://{host}:8091`：`/playground/microphone`（麦克风语音上传）、`/resource/file`（音频/模型文件下载）、`/health`。

## 质量门

```bash
cd zerolan-vtuber/server
uv run ruff check .   # lint
uv run mypy app       # 类型（strict）
uv run pytest         # 测试（当前 117 passed，覆盖率 86%）
```

CI 在 push/PR 时自动跑同三道闸（GitHub Actions）。

## 文档索引

| 文档 | 内容 |
|---|---|
| [server/README.md](zerolan-vtuber/server/README.md) | 服务端部署、config.yaml 逐项说明、免费配方、报错速查、协议摘要、Live2D 模型下发 |
| [client/README.md](zerolan-vtuber/client/README.md) | 客户端打包（团结云/本地 Unity）、首次运行配置、已知边界 |

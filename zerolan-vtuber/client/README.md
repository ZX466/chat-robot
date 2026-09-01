# zerolan-vtuber client(Unity 工程)

虚拟主播桌面宠物客户端(Unity 6000.0.51f1),配套服务端见 `../server`。
工程由原 ZerolanPlayground 资产生成 + 白名单脚本(§9/§12)合并而来。

## 工程结构

```
client/
├── Assets/
│   ├── Scenes/Main Scene.unity    # 入口场景(勿替换;如需新建场景请注册进 Build Settings)
│   ├── Resources/                 # 音频/字体/图标/UI Prefabs 等运行时资源
│   ├── Settings/                  # URP 渲染管线资产
│   ├── Scripts/                   # 51 个白名单脚本 + 3 个旧工程遗留文件(含 meta)
│   │   └── Handlers/ProviderConfigHandler.cs   # §9 新增:update_provider_config ack/掩码回显
│   ├── Editor/BuildScript.cs      # 云端/命令行打包入口(tj-builder 可调)
│   └── InputSystem_Actions.inputactions
├── Packages/manifest.json         # 依赖清单(UniTask/UnityWebSocket 为 git 引用,Editor 自动拉取)
└── ProjectSettings/               # Unity 6000.0.51f1 工程设置
```

## 打包前置条件(缺一不可)

1. **Live2D Cubism SDK for Unity**(唯一必须手动导入的外部组件):
   - 从 live2d.com 下载(免费注册),选支持 Unity 6 的版本(如 Cubism 5.x 最新);
   - 或找到旧工程完整备份中丢失的 `Assets/Live2D` 目录
   - 导入后确认 `LIVE2D_SDK_INSTALLED` 宏生效(SDK 通常自动定义)
2. 网络可用(Editor 首次打开会拉取 git 引用包:UniTask / UnityWebSocket)

## 打包步骤(团结/Unity Editor,一次性)

```text
1. 打开本目录(第一次打开会拉 UPM 包,耐心等待)
2. 确认宏状态(Project Settings > Player > Scripting Define Symbols):
   - 不定义: TRILIB_CORE_INSTALLED(3D 模型功能已裁)、VUFORIA_INSTALLED(AR 已裁)
   - 定义:   LIVE2D_SDK_INSTALLED(由 Live2D SDK 导入)
3. 修复编译错误(通常缺 TMP 字体资源,Unity 会提示自动创建;报错贴到项目 issue 即可)
4. File > Build Settings > Add Open Scene(Main Scene) > 平台选 Standalone Windows(64-bit) > Build
5. 产物:Build/zerolan-vtuber.exe
```

云端替代:本目录整体提交后,在团结云开发(Gitee 导入)按 `.workflows/windows.yaml`
自动构建——注意确认平台 runner 支持 Unity 6000 工程(模板 runner 为 2022.3 底座,
不匹配时需换 Unity 6 runner 或本地打包)。

## 联调信息

- 服务端默认 `http://127.0.0.1:8091` / `ws://127.0.0.1:8091/ws`(单端口)
- 客户端「设置」填目标服务器地址 → 连接(`client_hello` → `server_hello`)
- 「模型服务」分区:LLM(base_url/api_key/model)+ ASR/TTS(vendor+三元组)→ 发送
  `update_provider_config` 热替换(服务端仅内存生效,重启回落 config.yaml;api_key 不落盘)
- 当前供应商掩码在连上时 Toast 回显(如 `deepseek/d***`)

## 已知边界

- 无 Prefab 资产:UI 场景节点与 ConfigController 新字段需在场景 Prefab 中挂接
  (§12 第 4 项;仓库无 .prefab/.unity 之外的场景资产,字段留待 Editor 拖拽)
- 热替换 UI 的三组输入框在 `ConfigController`(`InitializeProviderConfigUi`)代码侧
  兜底 `Password` 类型与下拉选项,Editor 里拖好引用即可
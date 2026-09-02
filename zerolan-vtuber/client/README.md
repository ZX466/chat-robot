# zerolan-vtuber client(Unity 工程)

虚拟主播桌面宠物客户端,配套服务端部署见 `../server/README.md`。

- **Unity 版本:ProjectVersion.txt 记录 6000.0.51f1,但云构建 runner(Tuanjie 1.2.0)基座为 2022.3.2t13——依赖已按 2022.3 校准(URP 移除等),本地打开建议 2022.3.x**
- 渲染管线:内置 RP(URP 已移除)
- 输入:Input System 1.6.3,`activeInputHandler: 2`(Both,新旧兼容——勿改回 1,否则 UI 按钮全部失效)
- Live2D Cubism SDK:5-r.2 源码 + 5-r.5 的 Core DLL,已入仓库(`Assets/Live2D/`,约 2.2MB)

## 打包方式 A:团结云开发(推荐,无需本地 Unity)

本工程已通过团结云云构建出包,全程不用装 Unity Editor。

1. **平台仓库**:工程需在团结云开发(devops.u3dcloud.cn)的 Version Control(PlasticSCM)仓库中。
   本地平台工作区为 `D:/压缩包/chat-robot/client`,与 git 仓库改动**双同步**(改完 git 后手工拷贝对应文件过去)。
2. **构建配置**:仓库根 `.workflows/windows.yaml`——push 自动触发:
   - `checkout-plasticscm` 签出 → `tj-builder@v3`(targetPlatform: StandaloneWindows64,projectPath: ./tjcloudbuild)→ `tj-upload-artifact`
   - runner:`windows-server-2022-tuanjie-1.2.0-pc-8c-16g`
3. **触发**:平台工作区提交(Plastic checkin)→ push 自动构建;失败时下载构建日志排查
4. **产物**:构建成功后到构建页下载 artifact(压缩包含 `zerolan-vtuber.exe`)

> 注意:构建机**无法访问 github**,所有 UPM 依赖必须 vendor 进仓库
> (UniTask/UnityWebSocket 已在 `Packages/` 内,manifest 用 `file:` 引用,勿改回 git URL)。

## 打包方式 B:本地 Unity Editor

1. 用 **Unity 2022.3.x** 打开 `client/` 目录(首次打开自动导入 vendor 包)
2. 确认 Player Settings(已配置好,核对即可):
   - Scripting Define Symbols 含 `LIVE2D_SDK_INSTALLED`;不含 `TRILIB_CORE_INSTALLED`(3D/AR 已裁)
   - Active Input Handling:**Input System Package (New) 与 Old Both**
3. File > Build Settings > 场景列表含 `Assets/Scenes/Main Scene.unity` > Standalone Windows 64-bit > Build
4. 产物:`Build/zerolan-vtuber.exe`

## 首次运行配置

1. 先启动服务端(见 `../server/README.md` 快速部署)
2. 运行 exe → 点右上角**齿轮**(设置),面板内容:

   | 区块 | 操作 |
   |---|---|
   | **目标服务器** | 填 `ws://127.0.0.1:8091/ws` → 点**连接** |
   | **开关区** | 显示UI / 显示字幕 / 菜单置顶 / 启用AR模式(按需勾选) |
   | **模型服务(LLM)** | 填 Base URL(`https://api.deepseek.com/v1`)+ API Key(密码型,仅发服务端不落盘)+ Model(`deepseek/deepseek-chat`)→ 点**应用配置**(热替换,无需重启) |
   | **退出程序** | 关闭应用(或按 `Esc`) |

3. 连接成功:Toast 回显供应商掩码(如 `deepseek/d***`);服务端配了 `live2d_model` 时,**人物模型自动下载加载**(Toast"Live2D加载完毕"后进入桌宠透明模式)
4. 对话:客户端发文本 → 字幕 + 语音播报

> 换人物模型不用重新打包:替换服务端 `models/*.zip` + 改一行配置即可,见 `../server/README.md`。

## 已知边界

- ASR/TTS 的"模型服务"输入框暂未在场景挂接(只开放 LLM 三项);ASR/TTS 走服务端 `config.yaml` 配置
- 透明桌宠模式:`Esc` 退出;拖拽窗口移动
- 若 UI 按钮全部无法点击:检查 `ProjectSettings.asset` 的 `activeInputHandler` 必须为 `2`

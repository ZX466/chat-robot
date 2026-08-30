# fixtures

respx 契约测试使用的响应样本（任务书 §4.2：真实样本放 tests/fixtures/）。

> 注意：当前样本为按厂商公开 API 文档构造的结构占位（dev 环境无真实密钥抓包）。
> 后续拿到真实抓包响应后，请以同文件名替换为真实样本，测试断言无需改动
> （断言基于字段结构与语义，不绑定具体样本值，除测试内显式声明的常量外）。

文件清单：
- baidu_token_ok.json / baidu_token_error.json — 百度 OAuth token 成功/失败
- baidu_asr_ok.json / baidu_asr_err.json — 百度短语音识别 成功/err_no
- volcano_query_done.json — 火山 BigASR query 完成（utterances 聚合）
- baidu_tts_err.json — 百度 TTS JSON 错误响应
- mimo_tts_audio_json.json — MiMo TTS JSON 内嵌 base64 音频
  （data 为 b"fake-wav-from-b64" 的 base64，便于断言）

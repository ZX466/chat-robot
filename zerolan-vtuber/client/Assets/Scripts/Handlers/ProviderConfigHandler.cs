using System;
using System.Collections.Generic;
using Data;
using Framework;
using Newtonsoft.Json;
using UI;
using UnityEngine;

namespace Handlers
{
    /// <summary>
    /// update_provider_config ack 反馈 + server_hello 供应商掩码回显（§12 白名单）。
    /// DTO 内嵌本文件（Dto.cs 不在白名单，不得改动）。
    /// </summary>
    [Handler]
    public class ProviderConfigHandler : MonoBehaviour
    {
        [OnProtocolReceived(Action = Route.UpdateProviderConfig)]
        private void OnProviderConfigAck(ProviderConfigAck ack)
        {
            if (ack == null || string.IsNullOrEmpty(ack.Message))
            {
                ToastLogger.Error("供应商配置更新失败（无响应详情）");
                return;
            }

            ToastLogger.Info(ack.Message);
        }

        [OnProtocolReceived(Action = Route.ServerHello)]
        private void OnServerHello(ServerHelloWithProviders hello)
        {
            if (hello?.Providers == null)
            {
                return;
            }

            var parts = new List<string>();
            if (hello.Providers.TryGetValue("llm", out var llm))
            {
                parts.Add($"LLM {llm.Masked}");
            }

            if (hello.Providers.TryGetValue("asr", out var asr))
            {
                parts.Add($"ASR {asr.Masked}");
            }

            if (hello.Providers.TryGetValue("tts", out var tts))
            {
                parts.Add($"TTS {tts.Masked}");
            }

            if (parts.Count > 0)
            {
                ToastLogger.Info($"当前供应商：{string.Join(" / ", parts)}");
            }
        }

        private class ProviderConfigAck
        {
            public string Message { get; set; }

            [JsonConstructor]
            public ProviderConfigAck(string message)
            {
                Message = message;
            }
        }

        private class ServerHelloWithProviders
        {
            public int WsPort { get; set; }
            public int ResPort { get; set; }
            public string WsUrl { get; set; }
            public string HttpUrl { get; set; }
            public Dictionary<string, ProviderMask> Providers { get; set; }

            [JsonConstructor]
            public ServerHelloWithProviders(int wsPort, int resPort, string wsUrl, string httpUrl,
                Dictionary<string, ProviderMask> providers)
            {
                WsPort = wsPort;
                ResPort = resPort;
                WsUrl = wsUrl;
                HttpUrl = httpUrl;
                Providers = providers;
            }
        }

        private class ProviderMask
        {
            public string Provider { get; set; }
            public string Masked { get; set; }

            [JsonConstructor]
            public ProviderMask(string provider, string masked)
            {
                Provider = provider;
                Masked = masked;
            }
        }
    }
}
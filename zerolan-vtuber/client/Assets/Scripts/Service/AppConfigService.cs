using System;
using System.IO;
using Cysharp.Threading.Tasks;
using Data;
using Newtonsoft.Json;
using UnityEngine;

namespace Service
{
    public class AppConfigService
    {
        public string ConfigPath { private get; set; }
        private AppConfig _appConfig;
        public AppConfig Config => _appConfig;
        public static AppConfigService Instance { get; } = new();

        private AppConfigService()
        {
            _appConfig = new AppConfig(
                new ServiceConfig(ServiceType.WebSocket, "127.0.0.1", 11014),
                new ServiceConfig(ServiceType.Http, "127.0.0.1", 8899),
                new UIConfig(true, true, true),
                new DisplayModeConfig(false));
        }

        public async UniTask LoadConfig()
        {
            if (!File.Exists(ConfigPath))
            {
                Debug.Log("Config file dose not exist. Will not load config.");
                return;
            }

            var jsonString = await File.ReadAllTextAsync(ConfigPath);
            Debug.LogFormat("Config file content: {0}", jsonString);
            _appConfig = JsonConvert.DeserializeObject<AppConfig>(jsonString);
            Debug.LogFormat("Config file was loaded from: {0}", ConfigPath);
        }

        public async UniTask SaveConfig()
        {
            var jsonString = JsonConvert.SerializeObject(_appConfig);
            Debug.LogFormat("Config file content: {0}", jsonString);
            await File.WriteAllTextAsync(ConfigPath, jsonString);
            Debug.LogFormat("Config was saved at: {0}", ConfigPath);
        }

        public Uri GetWebSocketUri()
        {
            UriBuilder uriBuilder = new()
            {
                Host = _appConfig.WebSocketServer.Host,
                Port = _appConfig.WebSocketServer.Port,
                Scheme = "ws"
            };
            return uriBuilder.Uri;
        }
    }
}
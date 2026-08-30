/**
 * @Author: AkagawaTsurunaki
 */

using System;
using System.Collections.Generic;
using System.Linq;
using Controller;
using Cysharp.Threading.Tasks;
using Service;
using UI;
using Unity.VisualScripting;
using UnityEngine;
using UnityEngine.Assertions;
using Web.Api;
using GameObject = UnityEngine.GameObject;

namespace Framework
{
    public class Application : MonoBehaviour
    {
        private DependencyInjector _dependencyInjector;
        [SerializeField] private HandlersManager handlersManager;

        [SerializeField] private MicrophoneController microphoneController;
        [SerializeField] private ChatHistoryController chatHistoryController;
        [SerializeField] private bool debug;
        [SerializeField] private string wsUrl;

        private void Start()
        {
            UnityEngine.Application.logMessageReceived += OnLogMessageReceived;
            StartApplication().Forget();
        }

        private void OnDestroy()
        {
            UnityEngine.Application.logMessageReceived -= OnLogMessageReceived;
        }

        private static void OnLogMessageReceived(string condition, string stackTrace, LogType type)
        {
            if (type == LogType.Exception)
            {
                ToastLogger.Error($"未捕获异常：{condition}");
            }
        }

        private async UniTaskVoid StartApplication()
        {
            try
            {
                _dependencyInjector = this.AddComponent<DependencyInjector>();
                this.AddComponent<DesktopPetManager>();
                handlersManager.DestroyHandlers();
                AddAllDependencies();
                handlersManager.CreateHandlers(_dependencyInjector);

                WsApi.Client.EnableAutoReconnect();

                WsApi.Client.AddOnError(args =>
                {
                    if (string.IsNullOrWhiteSpace(args.Message))
                    {
                        ToastLogger.Error("连接出错：原因未知");
                    }
                    else
                    {
                        dict.TryGetValue(args.Message, out var message);
                        if (string.IsNullOrWhiteSpace(message))
                        {
                            message = args.Message;
                        }

                        ToastLogger.Error($"连接出错：{message}");
                    }
                });

#if UNITY_EDITOR
                if (debug)
                {
                    try
                    {
                        var uri = new Uri(wsUrl);
                        Debug.LogFormat("wsUrl: {0}", uri);
                        await WsApi.Client.ConnectAsync(uri.ToString());
                        ToastLogger.Info($"成功连接至远程服务器");
                    }
                    catch (Exception e)
                    {
                        Debug.LogException(e);
                    }
                }
#endif
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                ToastLogger.Error($"应用启动失败：{e.Message}");
            }
        }

        private static readonly Dictionary<string, string> dict = new()
        {
            { "Unable to connect to the remote server", "无法连接至远程服务器" },
            { "The remote party closed the WebSocket connection without completing the close handshake.", "远程服务器关闭了 WebSocket 连接，但是没有进行关闭握手。" }
        };

        /// Note: GameObject.Find with hardcoded path is intentional by design.
        /// Changing this would require a different DI approach.
        private void AddAllDependencies()
        {
            var controllerGo = GameObject.Find("Application/Controllers");
            var managerGo = GameObject.Find("Application/Managers");
            var controllers = new List<MonoBehaviour>();
            var managers = new List<MonoBehaviour>();

            if (controllerGo != null)
            {
                controllerGo.GetComponents(controllers);
            }
            if (managerGo != null)
            {
                managerGo.GetComponents(managers);
            }

            var allComponents = controllers.Concat(managers);
            foreach (var o in allComponents)
            {
                if (o == null) continue;
                _dependencyInjector.Dependencies.Add(o.GetType(), o);
            }

            _dependencyInjector.Dependencies.Add(typeof(MicrophoneController), microphoneController);
        }
    }
}
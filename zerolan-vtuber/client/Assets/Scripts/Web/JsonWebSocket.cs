/**
 * @Author: AkagawaTsurunaki
 */

using System;
using System.Collections.Generic;
using JetBrains.Annotations;
using Newtonsoft.Json;
using Newtonsoft.Json.Serialization;
using UnityEngine;
using UnityWebSocket;
using ErrorEventArgs = UnityWebSocket.ErrorEventArgs;
using Object = System.Object;

namespace Web
{
    public class CustomNamingStrategy : NamingStrategy
    {
        private readonly NamingStrategy _snakeCaseStrategy = new SnakeCaseNamingStrategy();

        protected override string ResolvePropertyName(string propertyName)
        {
            string snakeCaseName = _snakeCaseStrategy.GetPropertyName(propertyName, false);
            return char.ToLowerInvariant(snakeCaseName[0]) + snakeCaseName.Substring(1);
        }
    }

    public static class JsonConverter
    {
        private static readonly JsonSerializerSettings Settings = new()
        {
            ContractResolver = new DefaultContractResolver
            {
                NamingStrategy = new CustomNamingStrategy()
            }
        };

        public static string Serialize<T>(T t)
        {
            return JsonConvert.SerializeObject(t, Settings);
        }

        public static T DeSerialize<T>(string json)
        {
            return JsonConvert.DeserializeObject<T>(json, Settings);
        }

        public static Object DeserializeByType(string json, Type type)
        {
            return JsonConvert.DeserializeObject(json, type, Settings);
        }
    }

    public sealed class JsonWebSocketClient
    {
        public JsonWebSocketClient(string address)
        {
            _webSocket = new WebSocket(address);
        }

        public JsonWebSocketClient(string address, string subProtocol)
        {
            _webSocket = new WebSocket(address, subProtocol);
        }

        public JsonWebSocketClient(string address, string[] subProtocols)
        {
            _webSocket = new WebSocket(address, subProtocols);
        }

        public string Address => _webSocket.Address;
        public string[] SubProtocols => _webSocket.SubProtocols;
        public WebSocketState ReadyState => _webSocket.ReadyState;
        private readonly WebSocket _webSocket;

        // Delegate tracking for unsubscribable event handlers
        private readonly Dictionary<Action<OpenEventArgs>, EventHandler<OpenEventArgs>> _openHandlers = new();
        private readonly Dictionary<Action<CloseEventArgs>, EventHandler<CloseEventArgs>> _closeHandlers = new();
        private readonly Dictionary<Action<ErrorEventArgs>, EventHandler<ErrorEventArgs>> _errorHandlers = new();
        private readonly Dictionary<string, EventHandler<MessageEventArgs>> _messageHandlers = new();


        public void ConnectAsync()
        {
            _webSocket.ConnectAsync();
        }

        public void CloseAsync()
        {
            _webSocket.CloseAsync();
        }

        public void SendAsync(Object data)
        {
            var json = JsonConverter.Serialize(data);
            _webSocket.SendAsync(json);
            Debug.Log("Send json data: " + json);
        }

        public void AddOnOpen([NotNull] Action<OpenEventArgs> handler)
        {
            EventHandler<OpenEventArgs> wrapper = (sender, args) => { handler.Invoke(args); };
            _openHandlers[handler] = wrapper;
            _webSocket.OnOpen += wrapper;
        }

        public void RemoveOnOpen([NotNull] Action<OpenEventArgs> handler)
        {
            if (_openHandlers.TryGetValue(handler, out var wrapper))
            {
                _webSocket.OnOpen -= wrapper;
                _openHandlers.Remove(handler);
            }
        }

        public void AddOnClose([NotNull] Action<CloseEventArgs> handler)
        {
            EventHandler<CloseEventArgs> wrapper = (sender, args) => { handler.Invoke(args); };
            _closeHandlers[handler] = wrapper;
            _webSocket.OnClose += wrapper;
        }

        public void RemoveOnClose([NotNull] Action<CloseEventArgs> handler)
        {
            if (_closeHandlers.TryGetValue(handler, out var wrapper))
            {
                _webSocket.OnClose -= wrapper;
                _closeHandlers.Remove(handler);
            }
        }

        public void AddOnError([NotNull] Action<ErrorEventArgs> handler)
        {
            EventHandler<ErrorEventArgs> wrapper = (sender, args) => { handler.Invoke(args); };
            _errorHandlers[handler] = wrapper;
            _webSocket.OnError += wrapper;
        }

        public void RemoveOnError([NotNull] Action<ErrorEventArgs> handler)
        {
            if (_errorHandlers.TryGetValue(handler, out var wrapper))
            {
                _webSocket.OnError -= wrapper;
                _errorHandlers.Remove(handler);
            }
        }

        public void AddOnMessage<T>([NotNull] string key, [NotNull] Action<T> handler)
        {
            if (_messageHandlers.ContainsKey(key))
            {
                Debug.LogWarning($"[WS] Duplicate message handler key: {key}, replacing.");
                RemoveOnMessage(key);
            }

            EventHandler<MessageEventArgs> wrapper = (sender, args) =>
            {
                if (args.IsText)
                {
                    UnityEngine.Debug.Log("[WS] Raw message received: " + args.Data);
                    try
                    {
                        var obj = JsonConverter.DeSerialize<T>(args.Data);
                        handler.Invoke(obj);
                    }
                    catch (Exception e)
                    {
                        UnityEngine.Debug.LogError("[WS] Deserialize error: " + e.Message);
                    }
                }
            };
            _messageHandlers[key] = wrapper;
            _webSocket.OnMessage += wrapper;
        }

        public void RemoveOnMessage([NotNull] string key)
        {
            if (_messageHandlers.TryGetValue(key, out var wrapper))
            {
                _webSocket.OnMessage -= wrapper;
                _messageHandlers.Remove(key);
            }
        }
    }
}
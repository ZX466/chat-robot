using System;
using System.Collections.Generic;
using System.Threading;
using Cysharp.Threading.Tasks;
using Data;
using JetBrains.Annotations;
using UI;
using UnityEngine;
using UnityWebSocket;
using Object = System.Object;

namespace Web
{
    public class ConnectionClosedException : Exception
    {
        public ConnectionClosedException(string message) : base(message)
        {
        }
    }

    public class ConnectionTimeoutException : Exception
    {
        public ConnectionTimeoutException(string message) : base(message)
        {
        }
    }

    /// <summary>
    /// Author: AkagawaTsurunaki
    /// </summary>
    public class ZerolanProtocolClient
    {
        public ZerolanProtocolClient(string protocol = "ZerolanProtocol", string version = "1.1")
        {
            _protocol = protocol;
            _version = version;
        }

        private JsonWebSocketClient _webSocket;
        private readonly string _protocol;
        private readonly string _version;
        private bool _helloSent = false;
        private readonly List<Action<OpenEventArgs>> _onOpenListeners = new();
        private readonly List<Action<CloseEventArgs>> _onCloseListeners = new();
        private readonly List<Action<ErrorEventArgs>> _onErrorListeners = new();
        private readonly Dictionary<string, List<Action<Object>>> _onMessageListeners = new();
        public string Address => _webSocket?.Address;

        // Heartbeat
        private CancellationTokenSource _heartbeatCts;
        private const int HeartbeatIntervalSeconds = 15;

        // Reconnect
        private CancellationTokenSource _reconnectCts;
        private string _lastAddress;
        private bool _reconnectEnabled;
        private const int MaxReconnectAttempts = 5;
        private const int ReconnectBaseDelayMs = 1000;

        // Close completion tracking
        private UniTaskCompletionSource _closeTcs;

        // Thread safety for ConnectAsync
        private readonly SemaphoreSlim _connectLock = new SemaphoreSlim(1, 1);

        private void SendClientHello()
        {
            _webSocket.SendAsync(new ZerolanProtocol<Object>(_protocol, _version, "Client hello!",
                Route.ClientHello, 0, null));
            _helloSent = true;
        }

        public async UniTask ConnectAsync([NotNull] string address)
        {
            await _connectLock.WaitAsync();
            try
            {
                if (IsAlreadyConnected()) return;

                await WaitForCloseIfClosing();

                ToastLogger.Info("正在连接，请稍候……");

                InitializeWebSocket(address);
                await WaitForConnection(address);
            }
            finally
            {
                _connectLock.Release();
            }
        }

        private bool IsAlreadyConnected()
        {
            if (_webSocket == null) return false;

            if (_webSocket.ReadyState == WebSocketState.Open)
            {
                Debug.LogWarning("Connection already established, call `CloseAsync` before connecting new one.");
                return true;
            }

            return false;
        }

        private async UniTask WaitForCloseIfClosing()
        {
            if (_webSocket != null && _webSocket.ReadyState == WebSocketState.Closing)
            {
                Debug.Log("Waiting for previous connection to close...");
                if (_closeTcs != null)
                {
                    await _closeTcs.Task.Timeout(TimeSpan.FromSeconds(5)).SuppressCancellationThrow();
                }
            }
        }

        private void InitializeWebSocket(string address)
        {
            // Clear accumulated listeners to prevent duplicates on reconnect
            _onOpenListeners.Clear();
            _onCloseListeners.Clear();
            _onErrorListeners.Clear();

            _webSocket = new JsonWebSocketClient(address, _protocol);
            _helloSent = false;
            _lastAddress = address;
            AddOnError(args => { /* captured by closure below */ });
            AddOnOpen(args =>
            {
                SendClientHello();
                StartHeartbeat();
            });
            RegisterListener(_webSocket);
            _webSocket.ConnectAsync();
        }

        private async UniTask WaitForConnection(string address)
        {
            var closed = false;
            var reason = string.Empty;
            var error = string.Empty;
            AddOnClose(args =>
            {
                closed = true;
                reason = args.Reason;
            });
            AddOnError(args => { error = args.Message; });

            Debug.LogFormat("Connecting to {0}: Waiting for connection...", address);

            try
            {
                var cts = new CancellationTokenSource();
                await UniTask.WaitUntil(() => _webSocket.ReadyState == WebSocketState.Open,
                        cancellationToken: cts.Token)
                    .Timeout(TimeSpan.FromSeconds(3), taskCancellationTokenSource: cts);
            }
            catch (TimeoutException)
            {
                _webSocket = null;
                if (closed)
                {
                    throw new ConnectionClosedException($"Connection closed: {reason} ({error})");
                }

                throw new ConnectionTimeoutException($"Connection timed out ({error})");
            }

            Debug.LogFormat("Connected to {0}: Successful!", address);
        }

        private void RegisterListener(JsonWebSocketClient ws)
        {
            foreach (var onOpenListener in _onOpenListeners)
            {
                ws.AddOnOpen(args => { onOpenListener?.Invoke(args); });
            }

            foreach (var onCloseListener in _onCloseListeners)
            {
                ws.AddOnClose(args =>
                {
                    onCloseListener?.Invoke(args);
                    _closeTcs?.TrySetResult();
                    StopHeartbeat();
                    TryStartReconnect();
                });
            }

            foreach (var onErrorListener in _onErrorListeners)
            {
                ws.AddOnError(args => { onErrorListener?.Invoke(args); });
            }

            var msgIndex = 0;
            foreach (var (action, callbacks) in _onMessageListeners)
            {
                foreach (var callback in callbacks)
                {
                    var key = $"{action}_{msgIndex++}";
                    ws.AddOnMessage<ZerolanProtocol<Object>>(key, protocol =>
                    {
                        if (protocol.Protocol != _protocol)
                        {
                            return;
                        }

                        if (!IsVersionCompatible(protocol.Version))
                        {
                            return;
                        }

                        if (action == protocol.Action)
                        {
                            callback?.Invoke(protocol.Data);
                        }
                    });
                }
            }
        }


        public async UniTask CloseAsync()
        {
            StopHeartbeat();
            DisableAutoReconnect();

            if (_webSocket == null)
            {
                return;
            }

            if (_webSocket.ReadyState != WebSocketState.Open &&
                _webSocket.ReadyState != WebSocketState.Connecting)
            {
                _webSocket = null;
                return;
            }

            _closeTcs = new UniTaskCompletionSource();
            _webSocket.CloseAsync();

            try
            {
                await _closeTcs.Task.Timeout(TimeSpan.FromSeconds(3));
            }
            catch (TimeoutException)
            {
                Debug.LogWarning("CloseAsync timed out, forcing cleanup.");
            }

            _webSocket = null;
            _helloSent = false;
        }

        public void SendAsync(string action, Object data, string message = "")
        {
            if (!_helloSent)
            {
                throw new ConnectionClosedException("Send ClientHello first!");
            }

            if (_webSocket == null)
            {
                throw new ConnectionClosedException("WebSocket is not connected!");
            }

            var protocol = new ZerolanProtocol<Object>(_protocol, _version, message, action, 0, data);
            _webSocket.SendAsync(protocol);
        }

        public void AddOnOpen([NotNull] Action<OpenEventArgs> callback)
        {
            _onOpenListeners.Add(callback);
        }

        public void AddOnClose(Action<CloseEventArgs> callback)
        {
            _onCloseListeners.Add(callback);
        }

        public void AddOnError([NotNull] Action<ErrorEventArgs> callback)
        {
            _onErrorListeners.Add(callback);
        }

        public void AddOnMessage<T>([NotNull] string action, [NotNull] Action<Object> callback)
        {
            if (!_onMessageListeners.ContainsKey(action))
            {
                _onMessageListeners.Add(action, new List<Action<Object>>());
            }

            _onMessageListeners[action].Add(callback);
        }

        // --- Heartbeat ---

        private void StartHeartbeat()
        {
            StopHeartbeat();
            _heartbeatCts = new CancellationTokenSource();
            HeartbeatLoop(_heartbeatCts.Token).Forget();
        }

        private void StopHeartbeat()
        {
            if (_heartbeatCts != null)
            {
                _heartbeatCts.Cancel();
                _heartbeatCts.Dispose();
                _heartbeatCts = null;
            }
        }

        private async UniTaskVoid HeartbeatLoop(CancellationToken cancellationToken)
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                await UniTask.Delay(TimeSpan.FromSeconds(HeartbeatIntervalSeconds),
                    cancellationToken: cancellationToken).SuppressCancellationThrow();

                if (cancellationToken.IsCancellationRequested)
                {
                    break;
                }

                if (_webSocket == null || _webSocket.ReadyState != WebSocketState.Open)
                {
                    break;
                }

                try
                {
                    _webSocket.SendAsync(new ZerolanProtocol<Object>(_protocol, _version, "ping",
                        "ping", 0, null));
                }
                catch (Exception e)
                {
                    Debug.LogWarning($"Heartbeat send failed: {e.Message}");
                    break;
                }
            }
        }

        // --- Auto Reconnect ---

        public void EnableAutoReconnect()
        {
            _reconnectEnabled = true;
        }

        public void DisableAutoReconnect()
        {
            _reconnectEnabled = false;
            _reconnectCts?.Cancel();
            _reconnectCts?.Dispose();
            _reconnectCts = null;
        }

        private void TryStartReconnect()
        {
            if (!_reconnectEnabled || string.IsNullOrEmpty(_lastAddress))
            {
                return;
            }

            _reconnectCts?.Cancel();
            _reconnectCts?.Dispose();
            _reconnectCts = new CancellationTokenSource();
            ReconnectLoop(_reconnectCts.Token).Forget();
        }

        private async UniTaskVoid ReconnectLoop(CancellationToken cancellationToken)
        {
            for (int attempt = 1; attempt <= MaxReconnectAttempts; attempt++)
            {
                if (cancellationToken.IsCancellationRequested)
                {
                    return;
                }

                var delay = ReconnectBaseDelayMs * (1 << (attempt - 1));
                Debug.Log($"Reconnect attempt {attempt}/{MaxReconnectAttempts} in {delay}ms...");
                ToastLogger.Warning($"连接断开，{delay / 1000}秒后尝试重连 ({attempt}/{MaxReconnectAttempts})");

                await UniTask.Delay(delay, cancellationToken: cancellationToken).SuppressCancellationThrow();

                if (cancellationToken.IsCancellationRequested)
                {
                    return;
                }

                try
                {
                    await ConnectAsync(_lastAddress);
                    Debug.Log("Reconnect successful.");
                    ToastLogger.Info("重连成功");
                    return;
                }
                catch (Exception e)
                {
                    Debug.LogWarning($"Reconnect attempt {attempt} failed: {e.Message}");
                }
            }

            Debug.LogError("All reconnect attempts exhausted.");
            ToastLogger.Error("重连失败，请手动重新连接");
        }

        // --- Version Compatibility ---

        private bool IsVersionCompatible(string remoteVersion)
        {
            if (string.IsNullOrEmpty(remoteVersion))
            {
                Debug.LogWarning("Received empty protocol version, accepting anyway.");
                return true;
            }

            if (!TryParseVersion(_version, out var localMajor, out var localMinor))
            {
                Debug.LogWarning($"Failed to parse local protocol version: {_version}");
                return true;
            }

            if (!TryParseVersion(remoteVersion, out var remoteMajor, out var remoteMinor))
            {
                Debug.LogWarning($"Failed to parse remote protocol version: {remoteVersion}, accepting anyway.");
                return true;
            }

            if (remoteMajor != localMajor)
            {
                Debug.LogError(
                    $"Protocol major version mismatch: local={_version}, remote={remoteVersion}. Message rejected.");
                ToastLogger.Error($"协议版本不兼容：本地 {_version}，远端 {remoteVersion}");
                return false;
            }

            if (remoteMinor != localMinor)
            {
                Debug.LogWarning(
                    $"Protocol minor version mismatch: local={_version}, remote={remoteVersion}. Proceeding with caution.");
            }

            return true;
        }

        private static bool TryParseVersion(string version, out int major, out int minor)
        {
            major = 0;
            minor = 0;
            if (string.IsNullOrEmpty(version))
            {
                return false;
            }

            var parts = version.Split('.');
            if (parts.Length < 2)
            {
                return int.TryParse(parts[0], out major);
            }

            return int.TryParse(parts[0], out major) && int.TryParse(parts[1], out minor);
        }
    }
}

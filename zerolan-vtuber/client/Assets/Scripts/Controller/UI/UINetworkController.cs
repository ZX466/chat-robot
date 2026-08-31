using System;
using System.Threading;
using Cysharp.Threading.Tasks;
using JetBrains.Annotations;
using TMPro;
using UnityEngine;
using UnityEngine.Assertions;

namespace Controller.UI
{
    public enum NetworkConnectionStatus
    {
        Ready,
        Connected,
        Connecting,
        Disconnected,
    }

    public class UINetworkController : MonoBehaviour
    {
        [SerializeField] private TextMeshProUGUI ipAddressTextTMP;
        [SerializeField] private TextMeshProUGUI connectionDelayTMP;
        private bool _updateDelayInfoFlag = true;
        private string _ip;
        private CancellationTokenSource _pingCts;

        private void Start()
        {
            Assert.IsNotNull(ipAddressTextTMP);
            Assert.IsNotNull(connectionDelayTMP);
        }

        public void SetAddressTextValue(NetworkConnectionStatus status, string text = null)
        {
            if (status == NetworkConnectionStatus.Connected)
            {
                Assert.IsNotNull(text);
                ipAddressTextTMP.text = text;
            }
            else if (status == NetworkConnectionStatus.Connecting)
            {
                ipAddressTextTMP.text = "正在连接中……";
            }
            else if (status == NetworkConnectionStatus.Disconnected)
            {
                ipAddressTextTMP.text = "连接中断";
            }
            else if (status == NetworkConnectionStatus.Ready)
            {
                ipAddressTextTMP.text = "准备连接";
            }
        }


        public void StopPing()
        {
            _updateDelayInfoFlag = false;
            _pingCts?.Cancel();
            _pingCts?.Dispose();
            _pingCts = null;
        }

        public void StartPing([NotNull] string ip)
        {
            _ip = ip;
            if (!_updateDelayInfoFlag)
            {
                UpdateDelay().Forget();
            }
        }

        private async UniTaskVoid UpdateDelay()
        {
            while (_updateDelayInfoFlag)
            {
                if (_ip == null)
                {
                    await UniTask.WaitForSeconds(2);
                    continue;
                }

                var ping = new Ping(_ip);
                _pingCts?.Dispose();
                _pingCts = new CancellationTokenSource();
                try
                {
                    await UniTask.WaitUntil(() => ping.isDone, cancellationToken: _pingCts.Token)
                        .Timeout(TimeSpan.FromSeconds(1), taskCancellationTokenSource: _pingCts);
                }
                catch (Exception _)
                {
                    // ignored
                }

                connectionDelayTMP.text = ping.time <= 1 ? "<1 ms" : $"{ping.time} ms";
                ping.DestroyPing();
                await UniTask.WaitForSeconds(2);
            }
        }
    }
}
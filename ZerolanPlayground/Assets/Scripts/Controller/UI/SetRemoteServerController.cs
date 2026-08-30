using System;
using Cysharp.Threading.Tasks;
using TMPro;
using UI;
using UnityEngine;
using UnityEngine.UI;
using Web.Api;

namespace Controller.UI
{
    public class SetRemoteServerController : MonoBehaviour
    {
        [SerializeField] private TMP_InputField serverURLText;

        /// <summary>
        /// Connect Button
        /// </summary>
        [SerializeField] private Button connectButton;

        private void Start()
        {
            connectButton.onClick.AddListener(() => { ConnectServer().Forget(); });
        }

        private async UniTaskVoid ConnectServer()
        {
            Debug.Log("Connecting to remote server...");
            var url = serverURLText.text;
            url = url.Trim();
            try
            {
                await WsApi.Client.ConnectAsync(url);
                ToastLogger.Info("成功连接至远程服务器");
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                ToastLogger.Error($"连接失败：{e.Message}");
            }
        }
    }
}
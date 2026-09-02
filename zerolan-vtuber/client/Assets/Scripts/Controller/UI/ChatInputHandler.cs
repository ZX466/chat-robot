using System;
using System.Collections.Generic;
using Cysharp.Threading.Tasks;
using Data;
using TMPro;
using UI;
using UnityEngine;
using UnityEngine.UI;
using Web.Api;

namespace Controller.UI
{
    /// <summary>
    /// 文字聊天输入行（输入框 + 发送按钮），与语音并列的对话入口。
    /// 服务端宽松兜底：任何 action 携 data.text 均视为用户文本（server/app/api/ws.py），
    /// 回复复用现有字幕（show_user_text_input）与语音（play_speech）链路，无需额外处理。
    /// </summary>
    public class ChatInputHandler : MonoBehaviour
    {
        [SerializeField] private TMP_InputField chatInputField;
        [SerializeField] private Button sendButton;

        private void Awake()
        {
            if (chatInputField == null || sendButton == null)
            {
                Debug.LogError("[ChatInputHandler] 场景引用缺失：chatInputField / sendButton");
                return;
            }

            sendButton.onClick.AddListener(SendChat);
            chatInputField.onSubmit.AddListener(HandleSubmit);
        }

        private void HandleSubmit(string _)
        {
            SendChat();
            // 延迟一帧恢复焦点，便于连续输入；避开 onSubmit 同帧激活导致的双触发
            Refocus().Forget();
        }

        private async UniTaskVoid Refocus()
        {
            await UniTask.Yield(PlayerLoopTiming.LastPostLateUpdate);
            chatInputField.ActivateInputField();
        }

        private void SendChat()
        {
            var text = chatInputField != null ? chatInputField.text?.Trim() ?? string.Empty : string.Empty;
            if (string.IsNullOrEmpty(text))
            {
                return;
            }

            try
            {
                WsApi.Client.SendAsync(Route.Chat, new Dictionary<string, object> { ["text"] = text }, "Chat");
                chatInputField.text = string.Empty;
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                ToastLogger.Error($"发送失败：{e.Message}");
            }
        }
    }
}

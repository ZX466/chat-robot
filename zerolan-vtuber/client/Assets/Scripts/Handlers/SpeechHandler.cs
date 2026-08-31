using Controller;
using Cysharp.Threading.Tasks;
using Data;
using Framework;
using UnityEngine;
using Web;
using Web.Api;

namespace Handlers
{
    [Handler]
    public class SpeechHandler : MonoBehaviour
    {
        [Inject] private SpeechController SpeechController { get; set; }

        [Inject(GameObjectName = "User Text (TMP)")]
        private SubtitleController UserSubtitleController { get; set; }

        [Inject] private ChatHistoryController ChatHistoryController { get; set; }


        [OnProtocolReceived(Action = Route.PlaySpeech)]
        private void OnPlaySpeech(PlaySpeechResponse response)
        {
            PlaySpeech(response).Forget();
        }

        private async UniTaskVoid PlaySpeech(PlaySpeechResponse response)
        {
            Debug.LogFormat("`OnPlaySpeech` called");
            var controller = FindByBotId(response.BotId) ?? SpeechController;
            var audioClip = await HttpApi.Client.GetAudioClipAsync(response.FileId, response.AudioType);
            controller.AddAudioClip(audioClip, response.Transcript, response.Duration);
            Debug.Log($"Add speech: {response.FileId}");
        }

        [OnProtocolReceived(Action = Route.ShowUserTextInput)]
        private void OnShowUserTextInput(ShowUserTextInputResponse response)
        {
            Debug.LogFormat("`OnShowUserTextInput` called");
            UserSubtitleController.SetSubtitle(response.Text, 0);
        }

        [OnProtocolReceived(Action = Route.AddHistory)]
        private void OnAddHistory(AddChatHistory dto)
        {
            Debug.LogFormat("`OnAddHistory` called");
            if (dto.Role == "assistant")
            {
                ChatHistoryController.AddLeftChatBubble(dto.Username, dto.Text);
            }
            else if (dto.Role == "user")
            {
                ChatHistoryController.AddRightChatBubble(dto.Username, dto.Text);
            }
        }

        private SpeechController FindByBotId(string id)
        {
            var controllers = FindObjectsOfType<SpeechController>();

            foreach (var controller in controllers)
            {
                if (controller.BotId == id)
                {
                    return controller;
                }
            }

            return null;
        }
    }
}
using JetBrains.Annotations;
using UnityEngine;
using UnityEngine.Assertions;
using UnityEngine.UI;

namespace Controller
{
    public class ChatHistoryController : ClickableComponent
    {
        private GameObject _leftChatBubblePrefab;
        private GameObject _rightChatBubblePrefab;
        private GameObject _systemBubblePrefab;
        [SerializeField] private GameObject content;
        [SerializeField] private GameObject chatHistoryCanvas;
        [SerializeField] private Button chatHistoryButton;

        protected new void Start()
        {
            canvas = chatHistoryCanvas;
            button = chatHistoryButton;
            
            base.Start();
            
            _leftChatBubblePrefab = Resources.Load<GameObject>("Prefabs/Chat Bubble Left");
            _rightChatBubblePrefab = Resources.Load<GameObject>("Prefabs/Chat Bubble Right");
            _systemBubblePrefab = Resources.Load<GameObject>("Prefabs/System Bubble");
            Assert.IsNotNull(_leftChatBubblePrefab);
            Assert.IsNotNull(_rightChatBubblePrefab);
            Assert.IsNotNull(content);
        }

        public void AddSystemBubble([NotNull] string text)
        {
            var bubble = Instantiate(_systemBubblePrefab, content.transform);
            SetBubble(bubble, null, text);
        }

        public void AddLeftChatBubble([NotNull] string username, [NotNull] string text)
        {
            var bubble = Instantiate(_leftChatBubblePrefab, content.transform);
            SetBubble(bubble, username, text);
        }

        public void AddRightChatBubble([NotNull] string username, [NotNull] string text)
        {
            var bubble = Instantiate(_rightChatBubblePrefab, content.transform);
            SetBubble(bubble, username, text);
        }

        private void SetBubble(GameObject bubble, string username, [NotNull] string text)
        {
            var chatBubbleController = bubble.GetComponent<ChatBubbleController>();
            Assert.IsNotNull(chatBubbleController);
            chatBubbleController.SetContent(text);
            if (username != null)
            {
                chatBubbleController.SetUsername(username);
            }
        }
    }
}
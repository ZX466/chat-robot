using JetBrains.Annotations;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Controller
{
    public class ChatBubbleController : MonoBehaviour
    {
        [SerializeField] private TextMeshProUGUI contentTMP;
        [SerializeField] private TextMeshProUGUI usernameTMP;
        [SerializeField] private Image avatarImage;

        public void SetContent([NotNull] string content)
        {
            if (contentTMP != null)
            {
                contentTMP.text = content;
            }
        }

        public void SetUsername([NotNull] string username)
        {
            if (usernameTMP != null)
            {
                usernameTMP.text = username;
            }
        }
    }
}
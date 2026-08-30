using System;
using Cysharp.Threading.Tasks;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using Util;
using ColorUtility = UnityEngine.ColorUtility;

namespace UI
{
    public enum ToastType
    {
        Info,
        Warning,
        Error
    }

    public class Toast : MonoBehaviour
    {
        [SerializeField] private ToastType toastType;
        private AudioClip _warningSystemSound;
        private AudioClip _errorSystemSound;

        private TextMeshProUGUI _toastText;
        private Image _toastImage;
        private AudioSource _audioSource;
        private int fadeOutDuration = 3;

        private void Start()
        {
            InitComponents();
            InitSystemSounds();
            UpdateColor();
        }

        private void InitComponents()
        {
            if (_audioSource == null)
                _audioSource = GetComponent<AudioSource>();
            if (_toastImage == null)
                _toastImage = GetComponentInChildren<Image>();
            if (_toastText == null)
                _toastText = GetComponentInChildren<TextMeshProUGUI>();
        }

        private void InitSystemSounds()
        {
            if (_warningSystemSound == null)
                _warningSystemSound = Resources.Load<AudioClip>("Audio/System/warn");
            if (_errorSystemSound == null)
                _errorSystemSound = Resources.Load<AudioClip>("Audio/System/error");
        }


        public async UniTask Show(string text, ToastType level)
        {
            InitComponents();
            InitSystemSounds();
            _toastText.text = text;
            toastType = level;
            switch (toastType)
            {
                case ToastType.Info:
                    break;
                case ToastType.Warning:
                    _audioSource.clip = _warningSystemSound;
                    break;
                case ToastType.Error:
                    _audioSource.clip = _errorSystemSound;
                    break;
            }

            _audioSource.Play();

            await UniTask.Delay(TimeSpan.FromSeconds(Math.Clamp(_toastText.text.Length * 0.08f, 2f, 15f)));
#if DOTWEEN_UIMODULE_INSTALLED
            DoTweenUtil.DoFadeAll(gameObject, 0f, fadeOutDuration);
#endif
            Destroy(gameObject, fadeOutDuration + 1);
        }


        private void UpdateColor()
        {
            switch (toastType)
            {
                case ToastType.Info:
                    ColorUtility.TryParseHtmlString("#222222", out var infoToastImgColor);
                    ColorUtility.TryParseHtmlString("#ffffff", out var infoToastTxtColor);
                    _toastImage.color = infoToastImgColor;
                    _toastText.color = infoToastTxtColor;
                    break;
                case ToastType.Warning:
                    ColorUtility.TryParseHtmlString("#382c21", out var warningToastImgColor);
                    ColorUtility.TryParseHtmlString("#fa7a27", out var warningToastTxtColor);
                    _toastImage.color = warningToastImgColor;
                    _toastText.color = warningToastTxtColor;
                    break;
                case ToastType.Error:
                    ColorUtility.TryParseHtmlString("#352525", out var errorToastImgColor);
                    ColorUtility.TryParseHtmlString("#ff4f39", out var errorToastTxtColor);
                    _toastImage.color = errorToastImgColor;
                    _toastText.color = errorToastTxtColor;
                    break;
            }
        }
    }
}
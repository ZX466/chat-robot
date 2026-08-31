using System;
using System.Collections;
using TMPro;
using UnityEngine;

namespace Controller
{
    public class SubtitleController : MonoBehaviour
    {
        private TextMeshProUGUI _subtitleText; // 字幕的Text组件

        private bool _isSubtitleActive; // 字幕是否正在显示
        private const float FadeInDuration = 0.3f;
        private const float FadeOutDuration = 0.5f;

        private void Start()
        {
            _subtitleText = GetComponent<TextMeshProUGUI>();
            _subtitleText.text = "";
            SetAlpha(0f);
        }

        /// <summary>
        /// 设置字幕并开始显示
        /// </summary>
        /// <param name="text">字幕内容</param>
        /// <param name="duration">字幕显示的总时间</param>
        public void SetSubtitle(string text, float duration)
        {
            // 如果文本为空，直接返回
            if (string.IsNullOrEmpty(text))
            {
                return;
            }

            // 开始逐字打印
            StartCoroutine(PrintCharacter(text, duration));
        }

        private IEnumerator PrintCharacter(string text, float duration)
        {
            if (duration <= 0)
            {
                _subtitleText.text = text;
                SetAlpha(1f);
                yield break;
            }

            // Fade in
            yield return FadeAlpha(0f, 1f, FadeInDuration);

            // Calculate per-character delay from total duration
            float charDelay = duration / text.Length;
            charDelay = Mathf.Clamp(charDelay, 0.02f, 0.5f);

            _subtitleText.text = text;

            // 逐字打印
            for (int i = 0; i < text.Length; i++)
            {
                // 更新字幕内容
                _subtitleText.text = text.Substring(0, i + 1);
                // 等待一段时间
                yield return new WaitForSeconds(charDelay);
            }

            // Fade out
            yield return FadeAlpha(1f, 0f, FadeOutDuration);
            _subtitleText.text = "";
        }

        private IEnumerator FadeAlpha(float from, float to, float duration)
        {
            var color = _subtitleText.color;
            float elapsed = 0f;
            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                color.a = Mathf.Lerp(from, to, elapsed / duration);
                _subtitleText.color = color;
                yield return null;
            }

            color.a = to;
            _subtitleText.color = color;
        }

        private void SetAlpha(float alpha)
        {
            var color = _subtitleText.color;
            color.a = alpha;
            _subtitleText.color = color;
        }
    }
}
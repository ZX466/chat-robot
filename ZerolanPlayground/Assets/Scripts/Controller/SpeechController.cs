using System;
using System.Collections;
using System.Collections.Generic;
using Framework;
using JetBrains.Annotations;
using UnityEngine;
using UnityEngine.Networking;

namespace Controller
{
    public class SpeechController : MonoBehaviour
    {
        private string _botId;

        public string BotId
        {
            get => _botId;
            set
            {
                if (value != _botId)
                {
                    _botId = value;
                }
            }
        }

        [Inject(GameObjectName = "Bot Text (TMP)")] private SubtitleController _subtitleController { get; set; }

        class AudioMessage
        {
            public AudioClip AudioClip { get; set; }
            public string Text { get; set; }
            public float Duration { get; set; }

            public AudioMessage([NotNull] AudioClip audioClip, [NotNull] string text, float duration)
            {
                this.AudioClip = audioClip ?? throw new ArgumentNullException(nameof(audioClip));
                this.Text = text ?? throw new ArgumentNullException(nameof(text));
                this.Duration = duration;
            }
        }

        private const int MaxAudioMessages = 50;

        public AudioSource AudioSource { get; private set; }

        private readonly List<AudioMessage> _audioMessages = new();

        private void Start()
        {
            AudioSource = GetComponent<AudioSource>();
            if (AudioSource == null)
            {
                AudioSource = gameObject.AddComponent<AudioSource>();
            }

            StartCoroutine(Playing());
        }

        private IEnumerator Playing()
        {
            while (true)
            {
                // Should not use this statement because it will not check for each frame.
                // yield return new WaitWhile(() => audioManager.AudioSource.isPlaying);
                // Instead, use the following while statement:
                while (AudioSource.isPlaying || _audioMessages.Count == 0)
                {
                    yield return null;
                }

                // yield return new WaitUntil(() => AudioSource.isPlaying || _audioMessages.Count == 0);
                var audioMessage = _audioMessages[0];
                _audioMessages.RemoveAt(0);
                AudioSource.clip = audioMessage.AudioClip;
                AudioSource.Play();
                _subtitleController?.SetSubtitle(audioMessage.Text, audioMessage.Duration);
            }
        }

        public void AddAudioClip(AudioClip audioClip, string text, float duration)
        {
            if (_audioMessages.Count >= MaxAudioMessages)
            {
                var dropped = _audioMessages[0];
                _audioMessages.RemoveAt(0);
                Destroy(dropped.AudioClip);
                Debug.LogWarningFormat("Audio message queue full, dropping oldest message: {0}", dropped.Text);
            }

            _audioMessages.Add(new AudioMessage(audioClip, text, duration));
        }
    }
}
using Cysharp.Threading.Tasks;
using Data;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using Util;
using Web;
using Web.Api;

namespace Controller
{
    public class MicrophoneController : MonoBehaviour
    {
        // 是否开启麦克风
        private bool _isMicrophoneOn = false;

        // 麦克风图标按钮
        public Button SwitchMicrophoneButton;

        // 麦克风设备名
        private string _microphoneDeviceName;

        // 麦克风录音的AudioClip
        private AudioClip _microphoneRecording;

        // 音频源，用于播放麦克风录制的声音
        private AudioSource _audioSource;

        // 音量指示器
        [SerializeField] private Image volumeIndicator;

        private int _sampleRate = 16000;
        private const int VolumeSampleLength = 128;
        private float[] _volumeSamples;

        void Start()
        {
            SwitchMicrophoneButton.interactable = false;
            InitializeMicrophone();
            SwitchMicrophoneButton.onClick.AddListener(ToggleMicrophone);

            _audioSource = GetComponent<AudioSource>();
            if (_audioSource == null)
            {
                _audioSource = gameObject.AddComponent<AudioSource>();
            }

            _volumeSamples = new float[VolumeSampleLength];
            if (volumeIndicator != null)
            {
                volumeIndicator.fillAmount = 0f;
            }
        }

        private void InitializeMicrophone()
        {
            string[] devices = Microphone.devices;
            if (devices.Length == 0)
            {
                Debug.LogError("麦克风设备不可用！");
                return;
            }

            _microphoneDeviceName = devices[0];
            Debug.Log("麦克风设备名: " + _microphoneDeviceName);
        }

        private void Update()
        {
            if (!_isMicrophoneOn || _microphoneRecording == null || volumeIndicator == null)
            {
                return;
            }

            int micPosition = Microphone.GetPosition(_microphoneDeviceName);
            if (micPosition < VolumeSampleLength)
            {
                return;
            }

            _microphoneRecording.GetData(_volumeSamples, micPosition - VolumeSampleLength);

            float sum = 0f;
            for (int i = 0; i < VolumeSampleLength; i++)
            {
                sum += _volumeSamples[i] * _volumeSamples[i];
            }

            float rms = Mathf.Sqrt(sum / VolumeSampleLength);
            volumeIndicator.fillAmount = Mathf.Clamp01(rms * 10f);
        }

        public void EnableMicrophone()
        {
            SwitchMicrophoneButton.interactable = true;
        }

        // 切换麦克风开关
        private void ToggleMicrophone()
        {
            _isMicrophoneOn = !_isMicrophoneOn;

            if (_isMicrophoneOn)
            {
                // 开始麦克风录音
                // 采样率 16000 之外会报错
                _microphoneRecording = Microphone.Start(_microphoneDeviceName, true, 10, _sampleRate);
                Debug.Log("麦克风已开启");
            }
            else
            {
                // 停止麦克风录音
                Microphone.End(_microphoneDeviceName);
                Debug.Log("麦克风已关闭");
                if (volumeIndicator != null)
                {
                    volumeIndicator.fillAmount = 0f;
                }

                if (_microphoneRecording != null)
                {
                    Debug.Log($"播放音长 {_microphoneRecording.length} 秒");
                    // 防止阻塞 UI 更新
                    SendAudio().Forget();
                }
            }
            UpdateButtonText();
        }

        private async UniTask SendAudio()
        {
            var audioWaveData = WavUtility.FromAudioClip(_microphoneRecording);
            await HttpApi.Client.SendMicrophoneAudioAsync(audioWaveData, FileType.WAV, _microphoneRecording.frequency,
                _microphoneRecording.channels);
            DestroyMicrophoneRecording();
        }

        private void DestroyMicrophoneRecording()
        {
            if (_microphoneRecording != null)
            {
                Destroy(_microphoneRecording);
                _microphoneRecording = null;
            }
        }

        // 更新按钮文字
        private void UpdateButtonText()
        {
            if (SwitchMicrophoneButton != null)
            {
                var textMeshProUGUI = SwitchMicrophoneButton.GetComponentInChildren<TextMeshProUGUI>();
                if (textMeshProUGUI != null)
                    textMeshProUGUI.text = _isMicrophoneOn ? "Close Microphone" : "Open Microphone";
            }
        }
    }
}
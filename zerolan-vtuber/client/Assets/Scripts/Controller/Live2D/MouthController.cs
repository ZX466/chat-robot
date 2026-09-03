#if LIVE2D_SDK_INSTALLED
using System.Collections.Generic;
using Data;
using Live2D.Cubism.Core;
using Live2D.Cubism.Framework;
using Live2D.Cubism.Framework.MouthMovement;
using Unity.VisualScripting;
using UnityEngine;

namespace Controller.Live2D
{
    public class MouthController : MonoBehaviour
    {
        private CubismModel _model;

        private void Start()
        {
            _model = FindObjectOfType<CubismModel>();
            if (_model == null)
            {
                Debug.LogWarning("[MouthController] CubismModel not found in scene.");
                return;
            }
            SetMouthBehaviour();
        }

        private void SetMouthBehaviour()
        {
            // https://docs.live2d.com/zh-CHS/cubism-sdk-tutorials/lipsync/
            SetCubismMouthController();
            SetCubismAudioMouthInput();
            SetCubismMouthParameter();
        }

        private void SetCubismMouthController()
        {
            _model.AddComponent<CubismMouthController>();
            var mouthController = _model.GetComponent<CubismMouthController>();
            mouthController.BlendMode = CubismParameterBlendMode.Override;
            mouthController.MouthOpening = 1f;
        }

        private void SetCubismAudioMouthInput()
        {
            var audioSource = FindObjectOfType<AudioSource>();
            _model.AddComponent<CubismAudioMouthInput>();
            var audioMouthInput = _model.GetComponent<CubismAudioMouthInput>();
            if (audioSource == null)
            {
                // 语音播报 AudioSource 可能尚未创建：先不挂输入源，避免 NRE
                audioMouthInput.enabled = false;
                return;
            }
            audioMouthInput.AudioInput = audioSource;
            audioMouthInput.SamplingQuality = CubismAudioSamplingQuality.High;
            audioMouthInput.Gain = 10f;
            audioMouthInput.Smoothing = 1f;
        }

        private void SetCubismMouthParameter()
        {
            var paramList = new List<string> { Live2DParams.MouthOpenY };
            foreach (var paramId in paramList)
            {
                // 模型（如 Rice 缺 ParamMouthOpenY）可能缺标准参数：warn 并跳过，不炸整个加载链
                var param = _model.Parameters.FindById(paramId);
                if (param == null)
                {
                    Debug.LogWarning($"[{nameof(MouthController)}] 模型缺少参数，跳过：{paramId}");
                    continue;
                }
                param.AddComponent<CubismMouthParameter>();
            }
        }
    }
}
#endif
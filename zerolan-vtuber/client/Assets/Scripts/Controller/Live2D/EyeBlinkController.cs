#if LIVE2D_SDK_INSTALLED
using System.Collections.Generic;
using Data;
using Live2D.Cubism.Core;
using Live2D.Cubism.Framework;
using Unity.VisualScripting;
using UnityEngine;

namespace Controller.Live2D
{
    public class EyeBlinkController : MonoBehaviour
    {
        private CubismModel _model;
        private void Start()
        {
            _model = FindObjectOfType<CubismModel>();
            if (_model == null)
            {
                Debug.LogWarning("[EyeBlinkController] CubismModel not found in scene.");
                return;
            }
            SetAutoEyeBlinkBehaviour();
        }

        private void SetAutoEyeBlinkBehaviour()
        {
            // https://docs.live2d.com/zh-CHS/cubism-sdk-tutorials/eyeblink/
            SetCubismEyeBlinkController();
            SetCubismEyeBlinkParameter();
        }

        private void SetCubismEyeBlinkController()
        {
            _model.AddComponent<CubismAutoEyeBlinkInput>();
            var autoEyeBlinkInput = _model.GetComponent<CubismAutoEyeBlinkInput>();
            autoEyeBlinkInput.Mean = 2.5f;
            autoEyeBlinkInput.MaximumDeviation = 2f;
            autoEyeBlinkInput.Timescale = 10;

            _model.AddComponent<CubismEyeBlinkController>();
            var eyeBlinkController = _model.GetComponent<CubismEyeBlinkController>();
            eyeBlinkController.BlendMode = CubismParameterBlendMode.Override;
        }

        private void SetCubismEyeBlinkParameter()
        {
            var paramList = new List<string> { Live2DParams.EyeLOpen, Live2DParams.EyeROpen };
            foreach (var paramId in paramList)
            {
                // 模型可能缺标准参数：warn 并跳过，不炸整个加载链
                var param = _model.Parameters.FindById(paramId);
                if (param == null)
                {
                    Debug.LogWarning($"[{nameof(EyeBlinkController)}] 模型缺少参数，跳过：{paramId}");
                    continue;
                }
                param.AddComponent<CubismEyeBlinkParameter>();
            }
        }
    }
}
#endif
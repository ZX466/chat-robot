#if LIVE2D_SDK_INSTALLED
using System.Collections.Generic;
using Data;
using Live2D.Cubism.Core;
using Live2D.Cubism.Framework;
using Live2D.Cubism.Framework.HarmonicMotion;
using Unity.VisualScripting;
using UnityEngine;

namespace Controller.Live2D
{
    public class BreathController : MonoBehaviour
    {

        private CubismModel _model;
        private void Start()
        {
            _model = FindObjectOfType<CubismModel>();
            if (_model == null)
            {
                Debug.LogWarning("[BreathController] CubismModel not found in scene.");
                return;
            }
            SetBreathBehaviour();
        }

        private void SetBreathBehaviour()
        {
            SetCubismHarmonicMotionController();
            SetCubismHarmonicMotionParameter();
        }

        private void SetCubismHarmonicMotionController()
        {
            // https://docs.live2d.com/zh-CHS/cubism-sdk-tutorials/harmonicmotion/
            _model.AddComponent<CubismHarmonicMotionController>();
            var harmonicMotionController = _model.GetComponent<CubismHarmonicMotionController>();
            harmonicMotionController.BlendMode = CubismParameterBlendMode.Override;
            harmonicMotionController.ChannelTimescales = new List<float> { 1 }.ToArray();
        }
        private void SetCubismHarmonicMotionParameter()
        {
            var paramList = new List<string> { Live2DParams.BodyAngleY };
            foreach (var paramId in paramList)
            {
                // 模型（如 Rice）可能缺标准参数：warn 并跳过，不炸整个加载链
                var param = _model.Parameters.FindById(paramId);
                if (param == null)
                {
                    Debug.LogWarning($"[{nameof(BreathController)}] 模型缺少参数，跳过：{paramId}");
                    continue;
                }
                param.AddComponent<CubismHarmonicMotionParameter>();
                var harmonicMotionParam = param.GetComponent<CubismHarmonicMotionParameter>();
                harmonicMotionParam.Channel = 0;
                harmonicMotionParam.Direction = CubismHarmonicMotionDirection.Centric;
                harmonicMotionParam.NormalizedOrigin = 0.5f;
                harmonicMotionParam.NormalizedRange = 0.5f;
                harmonicMotionParam.Duration = 4;
            }
        }
    }
}
#endif
#if LIVE2D_SDK_INSTALLED
using System.Collections.Generic;
using Data;
using Live2D.Cubism.Core;
using Live2D.Cubism.Framework;
using Live2D.Cubism.Framework.LookAt;
using Unity.VisualScripting;
using UnityEngine;

namespace Controller.Live2D
{
    public class LookAtController : MonoBehaviour
    {
        private CubismModel _model;

        private void Start()
        {
            _model = FindObjectOfType<CubismModel>();
            if (_model == null)
            {
                Debug.LogWarning("[LookAtController] CubismModel not found in scene.");
                return;
            }
            SetLookAtBehaviour();
        }

        private void SetLookAtBehaviour()
        {
            // https://docs.live2d.com/zh-CHS/cubism-sdk-tutorials/lookat/
            SetModelCubismLookController();
            SetModelCubismLookParameters();
        }

        private void SetModelCubismLookController()
        {
            _model.AddComponent<CubismLookController>();
            var lookController = _model.GetComponent<CubismLookController>();
            lookController.BlendMode = CubismParameterBlendMode.Override;
            var target = FindObjectOfType<CubismLookTargetBehaviour>();
            if (target != null)
            {
                lookController.Target = target;
            }
            else
            {
                var cameraComp = FindObjectOfType<Camera>();
                if (cameraComp != null)
                {
                    target = cameraComp.AddComponent<CubismLookTargetBehaviour>();
                    lookController.Target = target;
                }
            }
        }

        private void SetModelCubismLookParameters()
        {
            var paramList = new List<string>() { Live2DParams.AngleX, Live2DParams.AngleY, Live2DParams.EyeBallX, Live2DParams.EyeBallY };
            foreach (var paramId in paramList)
            {
                var param = _model.Parameters.FindById(paramId) ??
                            throw new ModelParamException($"未找到参数：{paramId}");

                param.AddComponent<CubismLookParameter>();

                var lookParam = param.GetComponent<CubismLookParameter>();
                if (paramId.EndsWith("X"))
                {
                    lookParam.Axis = CubismLookAxis.X;
                }
                else if (paramId.EndsWith("Y"))
                {
                    lookParam.Axis = CubismLookAxis.Y;
                }

                lookParam.Factor = 50;
            }
        }
    }
}
#endif
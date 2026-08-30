#if LIVE2D_SDK_INSTALLED
using System;
using System.Collections.Generic;
using System.IO;
using Controller;
using Cysharp.Threading.Tasks;
using Data;
using Framework;
using JetBrains.Annotations;
using Live2D.Cubism.Core;
using Live2D.Cubism.Rendering;
using Unity.VisualScripting;
using UnityEngine;
using UnityEngine.Assertions;
using Util;
using Web.Api;
using Application = UnityEngine.Application;
using Transform = UnityEngine.Transform;

namespace Handlers
{
    [Handler]
    public class Live2DHandler : MonoBehaviour
    {
        private CubismModel _model;
        private List<AnimationClip> _animationClips;

        [Inject(GameObjectName = "Live2D Root")]
        private Transform Root { get; set; }

        [Inject] private ChatHistoryController ChatHistoryController { get; set; }
#if VUFORIA_INSTALLED
        [Inject] private CameraController CameraController { get; set; }
#endif

        [OnProtocolReceived(Action = Route.LoadLive2DModel)]
        private void OnLive2DLoad(LoadLive2DModelResponse data)
        {
            if (_model != null)
            {
                Debug.Log("Replacing existing Live2D model.");
                Destroy(_model.gameObject);
                _model = null;
                _animationClips = null;
            }

            LoadAll(data.ModelFileId).Forget();
        }

        private async UniTaskVoid LoadAll([NotNull] string fileId)
        {
            if (string.IsNullOrEmpty(fileId))
            {
                Debug.LogError("[Live2DHandler] fileId is null or empty.");
                return;
            }
            try
            {
                var modelZipPath = await HttpApi.Client.DownloadResourceFileAsync(fileId);
                var modelDir = ExtractModelZip(fileId, modelZipPath);
                if (string.IsNullOrEmpty(modelDir))
                {
                    ToastLogger.Error("模型解压失败：目录路径为空");
                    return;
                }
                InstantiateModel(modelDir);
            }
            catch (Exception ex)
            {
                Debug.LogError($"[Live2DHandler] 模型加载失败: {ex}");
                ToastLogger.Error($"模型加载失败: {ex.Message}");
            }
        }

        private void InstantiateModel(string modelDir)
        {
            // Locate model json path
            var modelPath = Live2DUtil.LocateModel3JsonPath(modelDir);
            Assert.IsNotNull(modelPath, "Failed to load model because `modelPath` is null.");
            Debug.LogFormat("Locate model from path: {0}", modelPath);

            _model = Live2DUtil.LoadModelFromPath(modelPath);
            try
            {
                _animationClips = Live2DUtil.LoadMotionsFromPath(_model, modelDir);
            }
            catch (Exception e)
            {
                Debug.LogException(e);
            }

            _model.transform.SetParent(Root);
            Live2DUtil.AddControllers(_model);
            _model.AddComponent<MeshRendererController>();
            // Avoid weird loading mode.
            SetRenderMode();

            _model.gameObject.transform.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
            // _model.gameObject.transform.localScale = Vector3.one * 7
#if VUFORIA_INSTALLED
            CameraController.AdjustCamera2d();
#endif
            AdjustCameraToFitModel();
            ChatHistoryController.AddSystemBubble("Live2D加载完毕");

            var desktopPet = FindObjectOfType<DesktopPetManager>();
            if (desktopPet != null)
            {
                desktopPet.EnterTransparentMode();
            }
        }


        private string ExtractModelZip([NotNull] string fileId, [NotNull] string zipFilePath)
        {
            return FileUtil.ExtractZipCached(fileId, zipFilePath);
        }

        private void SetRenderMode()
        {
            var renderController = _model.GetComponent<CubismRenderController>();
            if (renderController != null)
            {
                // 3D?
                renderController.SortingMode = CubismSortingMode.BackToFrontOrder;
            }
        }

        private void AdjustCameraToFitModel()
        {
            var mainCamera = Camera.main;
            if (mainCamera == null) return;

            // Calculate model bounds from all MeshRenderers
            var renderers = _model.GetComponentsInChildren<MeshRenderer>();
            if (renderers.Length == 0) return;

            var bounds = renderers[0].bounds;
            for (var i = 1; i < renderers.Length; i++)
            {
                bounds.Encapsulate(renderers[i].bounds);
            }

            // Position camera to look at the model center
            var center = bounds.center;
            var size = bounds.size;
            var maxExtent = Mathf.Max(size.x, size.y);

            // Camera looks from -Z toward +Z, model is in XY plane
            var distance = maxExtent / (2f * Mathf.Tan(mainCamera.fieldOfView * 0.5f * Mathf.Deg2Rad));
            mainCamera.transform.position = new Vector3(center.x, center.y, center.z - distance - 0.5f);
            mainCamera.transform.rotation = Quaternion.identity;

            Debug.LogFormat("Camera adjusted: pos={0}, model bounds={1}", mainCamera.transform.position, bounds);
        }
    }
}
#endif
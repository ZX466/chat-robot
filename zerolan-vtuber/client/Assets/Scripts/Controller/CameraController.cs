#if VUFORIA_INSTALLED && LIVE2D_SDK_INSTALLED
using System;
using System.Diagnostics;
using Cysharp.Threading.Tasks;
using Data;
using Live2D.Cubism.Core;
using UnityEngine;
using UnityEngine.Assertions;
using UnityEngine.UI;
using Vuforia;
using Web.Api;
using Debug = UnityEngine.Debug;
using Transform = UnityEngine.Transform;

namespace Controller
{
   public class CameraController : MonoBehaviour
    {
        [SerializeField] private Button cameraButton;
        [SerializeField] private Toggle enableArToggle;
        [SerializeField] private Transform imageTarget;
        private Camera _mainCamera;
        private VuforiaBehaviour _vuforiaBehaviour;
        private RenderTexture _cachedRT;
        private Texture2D _cachedScreenShot;

        private void Awake()
        {
            _mainCamera = Camera.main;
            _vuforiaBehaviour = _mainCamera.GetComponent<VuforiaBehaviour>();
            enableArToggle.onValueChanged.AddListener(OnToggleValueChanged);
        }

        private void OnDestroy()
        {
            if (_cachedRT != null)
            {
                _cachedRT.Release();
                Destroy(_cachedRT);
                _cachedRT = null;
            }

            if (_cachedScreenShot != null)
            {
                Destroy(_cachedScreenShot);
                _cachedScreenShot = null;
            }
        }

        private void Update()
        {
            _vuforiaBehaviour.enabled = enableArToggle.isOn;
        }

        private void OnToggleValueChanged(bool isOn)
        {
            if (isOn)
            {
                SwitchToARMode();
            }
            else
            {
                SwitchTo2DMode();
            }
        }

        private void SwitchTo2DMode()
        {
            cameraButton.interactable = false;
            _vuforiaBehaviour.enabled = false;
            AdjustCamera2d();
        }

        public void SwitchToARMode()
        {
            if (!VuforiaApplication.Instance.IsInitialized)
            {
                VuforiaApplication.Instance.Initialize();
            }

            cameraButton.interactable = true;
            _vuforiaBehaviour.enabled = true;
        }

        public void AdjustCamera2d()
        {
            _mainCamera.transform.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
            imageTarget.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
            var model = FindObjectOfType<CubismModel>();
            if (model == null)
            {
                Debug.LogWarningFormat("No need to adjust 2D camera because there is no model in the scene.");
                return;
            }

            var meshRendererController = model.GetComponent<MeshRendererController>();
            Assert.IsNotNull(meshRendererController, "MeshRendererController component is not found");

            var rectangle = meshRendererController.GetBounds();

            var smartCamera = _mainCamera.GetComponent<SmartCamera>();
            Assert.IsNotNull(smartCamera, "SmartCamera component is not found.");
            smartCamera.AdjustCameraToFitRectangle(rectangle);
        }


        private void Capture()
        {
            var screenShot = GetScreenShot();

            // Diagnostics for HTTP request cost => SendCameraImageAsync 0.13~0.14 sec
            var stopwatch = Stopwatch.StartNew();
            stopwatch.Start();
            HttpApi.Client.SendCameraImageAsync(screenShot.EncodeToPNG(), FileType.PNG).Forget();
            stopwatch.Stop();
            Debug.LogFormat(
                $"HttpApi.Client.SendCameraImageAsync finished in {stopwatch.Elapsed.TotalSeconds} seconds.");

            Debug.Log("Sent cameraAR image to server.");
        }

        // AkagawaTsurunaki 特别提醒
        // 这里不要使用 WebCamera 会导致和 Vuforia 的摄像机产生竞争而造成卡死
        private Texture2D GetScreenShot()
        {
            var width = _mainCamera.pixelWidth;
            var height = _mainCamera.pixelHeight;

            if (_cachedRT == null || _cachedRT.width != width || _cachedRT.height != height)
            {
                if (_cachedRT != null)
                {
                    _cachedRT.Release();
                    Destroy(_cachedRT);
                }

                _cachedRT = new RenderTexture(width, height, 0);
            }

            _mainCamera.targetTexture = _cachedRT;
            _mainCamera.Render();

            RenderTexture.active = _cachedRT;

            if (_cachedScreenShot == null || _cachedScreenShot.width != width || _cachedScreenShot.height != height)
            {
                if (_cachedScreenShot != null)
                {
                    Destroy(_cachedScreenShot);
                }

                _cachedScreenShot = new Texture2D(width, height, TextureFormat.RGB24, false);
            }

            _cachedScreenShot.ReadPixels(Rect.MinMaxRect(0, 0, width, height), 0, 0);
            _cachedScreenShot.Apply();

            _mainCamera.targetTexture = null;
            RenderTexture.active = null;
            return _cachedScreenShot;
        }
    }
}
#endif
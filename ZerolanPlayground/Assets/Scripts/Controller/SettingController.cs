using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem;
using UnityEngine.UI;

namespace Controller
{
    public class ClickableComponent : MonoBehaviour
    {
        protected Button button;
        protected GameObject canvas;

        protected void Start()
        {
            HideSettingCanvas();
            button.onClick.AddListener(() =>
            {
                if (canvas.activeSelf == false)
                {
                    ShowSettingCanvas();
                }
                else
                {
                    HideSettingCanvas();
                }
            });
        }

        private void ShowSettingCanvas()
        {
            canvas.SetActive(true);
        }

        private void HideSettingCanvas()
        {
            canvas.SetActive(false);
        }

        private void Update()
        {
            var touchscreen = Touchscreen.current;
            if (touchscreen != null && touchscreen.primaryTouch.press.wasPressedThisFrame)
            {
                var touchPosition = touchscreen.primaryTouch.position.ReadValue();
                if (!IsTouchOverUI(touchPosition))
                {
                    HideSettingCanvas();
                }
            }
        }

        // 判断触摸位置是否在 UI 上
        private bool IsTouchOverUI(Vector2 touchPosition)
        {
            var eventData = new PointerEventData(EventSystem.current)
            {
                position = touchPosition
            };

            var results = new List<RaycastResult>();
            EventSystem.current.RaycastAll(eventData, results);

            foreach (var result in results)
            {
                if (result.gameObject == canvas ||
                    result.gameObject.transform.IsChildOf(canvas.transform))
                {
                    return true; // 触摸位置在 Panel 或其子元素上
                }

                if (result.gameObject == button.gameObject ||
                    result.gameObject.transform.IsChildOf(button.transform))
                {
                    return true; // 触摸元素在 Setting 按钮本身上
                }
            }

            return false; // 触摸位置不在 Panel 上
        }
    }

    public class SettingController : ClickableComponent
    {
        [SerializeField] private Button settingButton;
        [SerializeField] private GameObject settingCanvas;

        private new void Start()
        {
            button = settingButton;
            canvas = settingCanvas;
            base.Start();
        }
    }
}
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Assertions;
using UnityEngine.UI;

namespace Controller.UI
{
    public class UIDisplayController : MonoBehaviour
    {
        [SerializeField] List<GameObject> canvases;
        [SerializeField] Toggle showUIToggle;
        [SerializeField] Toggle showSubtitleToggle;
        [SerializeField] GameObject subtitlePanel;
        [SerializeField] Canvas mainCanvas;
        [SerializeField] Toggle menuPositionToggle;
        [SerializeField] GameObject menuScrollView;

        private void Start()
        {
            Assert.IsNotNull(canvases);
            Assert.IsNotNull(showUIToggle);
            Assert.IsNotNull(showSubtitleToggle);
            Assert.IsNotNull(subtitlePanel);
            Assert.IsNotNull(mainCanvas);
            Assert.IsNotNull(menuPositionToggle);
            showUIToggle.onValueChanged.AddListener(isOn =>
            {
                if (isOn)
                {
                    showSubtitleToggle.interactable = true;
                    ShowSettingCanvas();
                }
                else
                {
                    showSubtitleToggle.interactable = false;
                    HideSettingCanvas();
                }
            });
            showSubtitleToggle.onValueChanged.AddListener(isOn =>
            {
                if (isOn)
                {
                    ShowSubtitlePanel();
                }
                else
                {
                    HideSubtitlePanel();
                }
            });
            menuPositionToggle.onValueChanged.AddListener(isOn =>
            {
                if (isOn)
                {
                    MoveMenuDown();
                }
                else
                {
                    MoveMenuUp();
                }
            });
        }

        private void ShowSettingCanvas()
        {
            foreach (var canvas in canvases)
            {
                if (canvas.name == "Chat Canvas")
                {
                    continue;
                }

                canvas.SetActive(true);
            }
        }

        private void HideSettingCanvas()
        {
            foreach (var canvas in canvases)
            {
                canvas.SetActive(false);
            }
        }


        private void ShowSubtitlePanel()
        {
            subtitlePanel.SetActive(true);
        }

        private void HideSubtitlePanel()
        {
            subtitlePanel.SetActive(false);
        }

        private void MoveMenuDown()
        {
            // 获取 Canvas 中的子节点数量
            int childCount = mainCanvas.transform.childCount;

            if (childCount < 2)
            {
                Debug.LogError("Canvas 中的子节点数量不足 2 个，无法将目标组件移动到倒数第二个位置");
                return;
            }

            // 计算目标位置（倒数第二个位置）
            int targetIndex = childCount - 2;

            // 将目标组件移动到目标位置
            menuScrollView.transform.SetSiblingIndex(targetIndex);
        }

        private void MoveMenuUp()
        {
            menuScrollView.transform.SetSiblingIndex(1);
        }
    }
}
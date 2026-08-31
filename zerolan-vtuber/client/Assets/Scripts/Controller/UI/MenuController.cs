using System.Collections.Generic;
using Cysharp.Threading.Tasks;
using Data;
using JetBrains.Annotations;
using TMPro;
using UnityEngine;
using UnityEngine.Assertions;
using Web;
using Web.Api;
using Button = UnityEngine.UI.Button;
using GameObject = UnityEngine.GameObject;
using Image = UnityEngine.UI.Image;
using Transform = UnityEngine.Transform;

namespace Controller.UI
{
    public class MenuController : MonoBehaviour
    {
        [SerializeField] private Transform scrollViewContent; // Scroll View的Content对象
        private GameObject _selectionItemPrefab;
        private readonly Dictionary<string, Sprite> _imageCache = new();
        private const int MaxCacheSize = 128;

        private void Awake()
        {
            _selectionItemPrefab = Resources.Load<GameObject>("Prefabs/Selection Button");
            Assert.IsNotNull(scrollViewContent);
        }

        public void DestroyLast()
        {
            foreach (Transform child in scrollViewContent)
            {
                Destroy(child.gameObject);
            }
        }


        // 生成按钮的方法
        public async UniTaskVoid GenerateButtons([NotNull] List<SelectionItem> selectionItems)
        {
            foreach (var item in selectionItems)
            {
                var selectionItemButton = Instantiate(_selectionItemPrefab, scrollViewContent);

                var button = selectionItemButton.GetComponent<Button>();
                var textMeshProUGUI = button.GetComponentInChildren<TextMeshProUGUI>();
                textMeshProUGUI.text = item.Text;

                if (!string.IsNullOrEmpty(item.ImgId))
                {
                    var targetImage = selectionItemButton.GetComponent<Image>();
                    if (targetImage == null)
                    {
                        Debug.LogError($"Target image is not set for {item.ImgId} because Image component is null.");
                        continue;
                    }

                    if (!_imageCache.TryGetValue(item.ImgId, out var sprite))
                    {
                        var texture = await HttpApi.Client.GetImageTextureAsync(item.ImgId);
                        var rect = new Rect(0, 0, texture.width, texture.height);
                        var pivot = Vector2.zero;
                        sprite = Sprite.Create(texture, rect, pivot);
                        if (_imageCache.Count >= MaxCacheSize)
                        {
                            _imageCache.Clear();
                        }
                        _imageCache[item.ImgId] = sprite;
                    }

                    targetImage.sprite = sprite;
                }
            }
        }
    }
}
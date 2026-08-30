#if DOTWEEN_UIMODULE_INSTALLED
using System;
using System.Collections.Generic;
using DG.Tweening;
using JetBrains.Annotations;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Util
{
    /// <summary>
    /// Reference:
    ///   https://blog.csdn.net/Q672405097/article/details/119705780
    /// </summary>
    public static class DoTweenUtil
    {
        public static void DoBlingBling([NotNull] GameObject go, float intervalEndValue, float duration,
            int loops)
        {
            var imageCompoList = new List<Image>(go.GetComponents<Image>());
            imageCompoList.AddRange(go.GetComponentsInChildren<Image>());

            var tmpCompsList = new List<TextMeshProUGUI>(go.GetComponents<TextMeshProUGUI>());
            tmpCompsList.AddRange(go.GetComponentsInChildren<TextMeshProUGUI>());

            imageCompoList.ForEach(image => DoBlingBlingForImage(image, intervalEndValue, duration, loops));
            tmpCompsList.ForEach(tmp => DoBlingBlingForTMP(tmp, intervalEndValue, duration, loops));
        }

        public static void DoBlingBlingForTMP(TextMeshProUGUI tmp, float intervalEndValue, float duration,
            int loops)
        {
            var sq = DOTween.Sequence();
            //第一个参数表示透明度  范围是[0,1] ,后面一个参数是经历时间,可以自行调节一个合适值
            sq.Append(tmp.DOFade(intervalEndValue, duration));
            sq.Append(tmp.DOFade(1, duration));
            sq.SetLoops(loops);
        }

        public static void DoBlingBlingForImage(Image image, float intervalEndValue, float duration,
            int loops)
        {
            var sq = DOTween.Sequence();
            //第一个参数表示透明度  范围是[0,1] ,后面一个参数是经历时间,可以自行调节一个合适值
            sq.Append(image.DOFade(intervalEndValue, duration));
            sq.Append(image.DOFade(1, duration));
            sq.SetLoops(loops);
        }

        public static void DoFadeAll([NotNull] GameObject go, float endValue, float duration,
            Action onComplete = null)
        {
            var imageComp = go.GetComponent<Image>();
            foreach (var componentsInChild in go.GetComponentsInChildren<Image>())
            {
                componentsInChild.DOFade(endValue, duration);
            }

            foreach (var componentsInChild in go.GetComponentsInChildren<TextMeshProUGUI>())
            {
                componentsInChild.DOFade(endValue, duration);
            }

            if (imageComp != null)
            {
                imageComp.DOFade(endValue, duration).OnComplete(() => onComplete?.Invoke());
            }
        }
    }
}
#endif
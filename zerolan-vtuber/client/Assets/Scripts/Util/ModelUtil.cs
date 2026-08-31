#if TRILIB_CORE_INSTALLED
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Data;
using JetBrains.Annotations;
using TriLibCore;
using UnityEngine;
using GameObject = UnityEngine.GameObject;

namespace Util
{
    public static class ModelUtil
    {
        public static void LoadModelFromDir([NotNull] string modelDir,
            [NotNull] Action<GameObject, AnimationClip[]> onFinished,
            Action<float> onProgress = null,
            Action onError = null)
        {
            var modelFiles = new List<string>();
            FileUtil.Walk(modelDir, file =>
            {
                var extension = Path.GetExtension(file).ToLower();
                if (modelFileTypes.Contains(extension))
                {
                    modelFiles.Add(file);
                }
            });

            Debug.Log(modelFiles.Count > 0
                ? $"Find {modelFiles.Count} model file(s) in {modelDir}"
                : $"No model files found in {modelDir}");

            // Only the first found model file will be instantiated
            var modelPath = modelFiles.First();
            LoadModel(modelPath, onFinished, onProgress, onError);
        }

        private static readonly HashSet<string> modelFileTypes = new()
        {
            "." + FileType.GLB.ToString().ToLower(),
            "." + FileType.GLTF.ToString().ToLower(),
            "." + FileType.FBX.ToString().ToLower(),
            "." + FileType.PMX.ToString().ToLower()
        };


        public static void LoadModel(string modelPath,
            [NotNull] Action<GameObject, AnimationClip[]> onFinished,
            Action<float> onProgress = null,
            Action onError = null)
        {
            var assetLoaderOptions = AssetLoader.CreateDefaultLoaderOptions();
            AssetLoader.LoadModelFromFile(modelPath, (context) =>
                {
                    var loadedObject = context.RootGameObject;
                    var animations = ExtractAnimationClips(loadedObject);
                    onFinished(loadedObject, animations);
                }, null, (_, progress) => { onProgress?.Invoke(progress); }, _ => { onError?.Invoke(); }, null,
                assetLoaderOptions);
        }

        private static AnimationClip[] ExtractAnimationClips(GameObject loadedObject)
        {
            if (loadedObject == null)
            {
                return Array.Empty<AnimationClip>();
            }

            var animator = loadedObject.GetComponent<Animator>();
            return animator != null ? animator.runtimeAnimatorController.animationClips : Array.Empty<AnimationClip>();
        }
    }
}
#endif
#if LIVE2D_SDK_INSTALLED
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Controller.Live2D;
using JetBrains.Annotations;
using Live2D.Cubism.Core;
using Live2D.Cubism.Framework.Json;
using Unity.VisualScripting;
using UnityEngine;

namespace Util
{
    public static class Live2DUtil
    {
        public static string LocateModel3JsonPath([NotNull] string dir)
        {
            var model3JsonPaths = new HashSet<string>();
            FileUtil.TraverseFolders(dir, file =>
            {
                if (Path.GetFileName(file).Contains(".model3.json"))
                {
                    model3JsonPaths.Add(file);
                }
            });
            if (model3JsonPaths.Count > 1)
            {
                var msg = model3JsonPaths.Aggregate("", (current, model3JsonPath) => current + ("\n" + model3JsonPath));
                throw new NotSupportedException($"Too many *.model3.json files found: {msg}");
            }

            if (model3JsonPaths.Count == 0)
            {
                throw new FileNotFoundException("*.model3.json file not found.");
            }

            return model3JsonPaths.First();
        }

        public static CubismModel LoadModelFromPath([NotNull] string modelPath)
        {
            var model3Json = CubismModel3Json.LoadAtPath(modelPath, BuiltinLoadAssetAtPath);
            var model = model3Json.ToModel();
            return model;
        }

        public static void AddControllers([NotNull] CubismModel model)
        {
            model.AddComponent<BreathController>();
            model.AddComponent<EyeBlinkController>();
            model.AddComponent<LookAtController>();
            model.AddComponent<MouthController>();
        }

        public static List<AnimationClip> LoadMotionsFromPath(CubismModel model, string motionsDir)
        {
            var animationClips = new List<AnimationClip>();
            var animation = model.AddComponent<Animation>();
            if (animation == null)
            {
                Debug.LogWarning("[Live2DUtil] Failed to add Animation component to model.");
                return animationClips;
            }
            FileUtil.TraverseFolders(motionsDir, (file) =>
            {
                if (file.Contains(".motion3.json"))
                {
                    var json = File.ReadAllText(file);
                    var motion3Json = CubismMotion3Json.LoadFrom(json);
                    var animationClip = motion3Json.ToAnimationClip();
                    animationClip.legacy = true;
                    var animName = Path.GetFileNameWithoutExtension(file);
                    animationClip.name = animName;
                    animationClips.Add(animationClip);
                }
            });

            foreach (var animationClip in animationClips)
            {
                animation.AddClip(animationClip, animationClip.name);
            }

            animation.Play(animationClips[0].name);
            return animationClips;
        }

        /// <summary>
        /// Load asset.
        /// </summary>
        /// <param name="assetType">Asset type.</param>
        /// <param name="absolutePath">Path to asset.</param>
        /// <returns>The asset on succes; <see langword="null"> otherwise.</returns>
        private static object BuiltinLoadAssetAtPath(Type assetType, string absolutePath)
        {
            switch (assetType)
            {
                case not null when assetType == typeof(byte[]):
                    return File.ReadAllBytes(absolutePath);
                case not null when assetType == typeof(string):
                    return File.ReadAllText(absolutePath);
                case not null when assetType == typeof(Texture2D):
                    var texture = new Texture2D(1, 1);
                    texture.LoadImage(File.ReadAllBytes(absolutePath));
                    return texture;
                default:
                    throw new NotSupportedException();
            }
        }
    }
}
#endif
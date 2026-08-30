using Data;
using DG.Tweening;
using Extension;
using Framework;
using UnityEngine;
using GameObjectInfo = Data.GameObjectInfo;
using Transform = Data.Transform;

namespace Controller.AR
{
    public class ModelController : MonoBehaviour
    {
        public string ModelName { get; set; }
        [Inject(GameObjectName = "Root")] private UnityEngine.Transform Root { get; set; }

        public void SetScale(float k, float duration = 2.0f)
        {
            var targetScale = Vector3.one * k;
            DOTween.To(() => transform.localScale, curScale => { transform.localScale = curScale; },
                    targetScale, duration)
                .SetEase(Ease.InOutQuart).SetUpdate(true);
        }


        private static string GetBuiltinResourcePath(BuiltinGameObjectType objectType)
        {
            return objectType switch
            {
                BuiltinGameObjectType.Cube => "Cube.fbx",
                BuiltinGameObjectType.Sphere => "Sphere.fbx",
                BuiltinGameObjectType.Cylinder => "Cylinder.fbx",
                BuiltinGameObjectType.Capsule => "Capsule.fbx",
                BuiltinGameObjectType.Plane => "Plane.fbx",
                _ => "Sphere.fbx"
            };
        }

        public static void CreateGameObject(CreateGameObjectResponse response, UnityEngine.Transform parent)
        {
            var go = new UnityEngine.GameObject(response.GameObjectName)
            {
                transform =
                {
                    localScale = Vector3.zero,
                    parent = parent
                }
            };

            AddMeshComponents(go, response);
            var modelController = go.AddComponent<ModelController>();
            modelController.ModelName = response.GameObjectName;
            modelController.SetScale(response.Transform.Scale);
            go.transform.position = response.Transform.Position.ToVec3();
            go.AddComponent<BoxCollider>();
        }

        private static void AddMeshComponents(UnityEngine.GameObject go, CreateGameObjectResponse response)
        {
            go.AddComponent<MeshFilter>().mesh =
                Resources.GetBuiltinResource<Mesh>(GetBuiltinResourcePath(response.ObjectType));
            var meshRenderer = go.AddComponent<MeshRenderer>();
            if (meshRenderer != null)
            {
                meshRenderer.material.color = Color.white.FromString(response.Color);
            }
        }


        public GameObjectInfo ToGameObjectInfo()
        {
            var go = gameObject;
            var position = new Position(go.transform.position.x, go.transform.position.y, go.transform.position.z);
            var transformData = new Transform(go.transform.localScale.x, position);
            return new GameObjectInfo(go.GetInstanceID(), ModelName, transformData);
        }
    }
}
using Cysharp.Threading.Tasks;
using System.IO;
using System.Linq;
using Controller.AR;
using Data;
using Framework;
using JetBrains.Annotations;
using UnityEngine;
using Util;
using Web.Api;
using Application = UnityEngine.Application;
using FileInfo = Data.FileInfo;
using Transform = UnityEngine.Transform;

namespace Handlers
{
    [Handler]
    public class Model3DActionHandler : MonoBehaviour
    {
        [Inject(GameObjectName = "Root")] private Transform Root { get; set; }

        [OnProtocolReceived(Action = Route.Load3DModel)]
        private void OnLoadModel(FileInfo fileInfo)
        {
            Load3dModel(fileInfo.FileId, fileInfo.FileName);
            UpdateGameObjectsInfo();
        }

        private async UniTaskVoid Load3dModel(string fileId, string fileName)
        {
            var path = await HttpApi.Client.DownloadResourceFileAsync(fileId);
            var modelDir = ExtractModelZip(fileId, path);
#if TRILIB_CORE_INSTALLED
            ModelUtil.LoadModelFromDir(modelDir, (go, clips) =>
            {
                if (go == null)
                {
                    Debug.LogErrorFormat("Failed to load model from {0} due to the null game object", modelDir);
                    return;
                }

                var model = Instantiate(go, Root, true);
                var modelController = model.AddComponent<ModelController>();
                modelController.ModelName = fileName;
                model.GetInstanceID();
            });
#endif
        }

        private string ExtractModelZip([NotNull] string fileId, [NotNull] string zipFilePath)
        {
            return FileUtil.ExtractZipCached(fileId, zipFilePath, recursive: true);
        }


        [OnProtocolReceived(Action = Route.ModifyGameObjectScale)]
        private void OnModifyGameObjectScale(ScaleOperationResponse so)
        {
            var modelControllers = Root.GetComponentsInChildren<ModelController>();
            foreach (var modelController in modelControllers)
            {
                if (modelController.gameObject.GetInstanceID() != so.InstanceId) continue;
                modelController.SetScale(so.TargetScale);
                return;
            }

            UpdateGameObjectsInfo();
        }

        [OnProtocolReceived(Action = Route.CreateGameObject)]
        private void OnCreateGameObject(CreateGameObjectResponse response)
        {
            if (response == null)
            {
                Debug.LogErrorFormat("No create game object dto was provided");
                return;
            }

            ModelController.CreateGameObject(response, Root);
            UpdateGameObjectsInfo();
        }

        [OnProtocolReceived(Action = Route.QueryGameObjectsInfo)]
        private void OnQueryGameObjectsInfo()
        {
            UpdateGameObjectsInfo();
        }

        private void UpdateGameObjectsInfo()
        {
            var modelControllers = Root.GetComponentsInChildren<ModelController>();
            var gameObjectInfos =
                modelControllers.Select(modelController => modelController.ToGameObjectInfo()).ToList();
            WsApi.Client.SendAsync(Route.UpdateGameObjectsInfo, gameObjectInfos);
        }
    }
}
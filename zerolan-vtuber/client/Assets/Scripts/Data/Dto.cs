using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEngine;

namespace Data
{
    public class PlaySpeechResponse
    {
        public string BotId { get; set; }
        public string BotDisplayName { get; set; }
        public string FileId { get; set; }
        public string Transcript { get; set; }
        public string AudioType { get; set; }
        public float Duration { get; set; }
        public int Channels { get; set; }
        public int SampleRate { get; set; }

        [JsonConstructor]
        public PlaySpeechResponse(string botId, string botDisplayName, string fileId, string transcript,
            string audioType,
            float duration, int channels, int sampleRate)
        {
            BotId = botId;
            BotDisplayName = botDisplayName;
            FileId = fileId;
            Transcript = transcript;
            AudioType = audioType;
            Duration = duration;
            Channels = channels;
            SampleRate = sampleRate;
        }
    }

    public class LoadLive2DModelResponse
    {
        public string BotId { get; set; }
        public string BotDisplayName { get; set; }
        public string ModelFileId { get; set; }

        [JsonConstructor]
        public LoadLive2DModelResponse(string botId, string botDisplayName, string modelDir,
            string modelFileId)
        {
            BotId = botId;
            BotDisplayName = botDisplayName;
            ModelFileId = modelFileId;
        }
    }

    public class FileInfo
    {
        public string FileId { get; set; }
        public string Uri { get; set; }
        public FileType FileType { get; set; }
        public string OriginFileName { get; set; }
        public string FileName { get; set; }
        public long FileSize { get; set; }

        [JsonConstructor]
        public FileInfo(string fileId, string uri, FileType fileType, string originFileName, string fileName,
            long fileSize, string sha256)
        {
            FileId = fileId;
            Uri = uri;
            FileType = fileType;
            OriginFileName = originFileName;
            FileName = fileName;
            FileSize = fileSize;
        }
    }

    public class Position
    {
        public float X { get; set; }
        public float Y { get; set; }
        public float Z { get; set; }

        public Position(float x, float y, float z)
        {
            X = x;
            Y = y;
            Z = z;
        }

        public Vector3 ToVec3()
        {
            return new Vector3(X, Y, Z);
        }
    }

    public class Transform
    {
        public float Scale { get; set; }
        public Position Position { get; set; }

        public Transform(float scale, Position position)
        {
            Scale = scale;
            Position = position;
        }
    }


    public class GameObjectInfo
    {
        public int InstanceId { get; set; }
        public string GameObjectName { get; set; }
        public Transform Transform { get; set; }


        [JsonConstructor]
        public GameObjectInfo(int instanceId, string gameObjectName, Transform transform)
        {
            InstanceId = instanceId;
            GameObjectName = gameObjectName;
            Transform = transform;
        }
    }

    public class ScaleOperationResponse
    {
        public int InstanceId { get; set; }
        public float TargetScale { get; set; }

        public ScaleOperationResponse(int instanceId, float targetScale)
        {
            InstanceId = instanceId;
            TargetScale = targetScale;
        }
    }

    public class CreateGameObjectResponse
    {
        public int InstanceId { get; set; }
        public string GameObjectName { get; set; }
        public BuiltinGameObjectType ObjectType { get; set; }
        public string Color { get; set; }
        public Transform Transform { get; set; }

        [JsonConstructor]
        public CreateGameObjectResponse(int instanceId, string gameObjectName, BuiltinGameObjectType objectType,
            string color,
            Transform transform)
        {
            InstanceId = instanceId;
            GameObjectName = gameObjectName;
            ObjectType = objectType;
            Color = color;
            Transform = transform;
        }
    }

    public class ShowUserTextInputResponse
    {
        public string Text { get; set; }

        [JsonConstructor]
        public ShowUserTextInputResponse(string text)
        {
            Text = text;
        }
    }

    public class ServerHello
    {
        public int WsPort { get; set; }
        public int ResPort { get; set; }
        public LoadLive2DModelResponse Live2DModel { get; set; }

        [JsonConstructor]
        public ServerHello(int wsPort, int resPort)
        {
            WsPort = wsPort;
            ResPort = resPort;
        }
    }

    public class AddChatHistory
    {
        public string Role { get; set; }
        public string Text { get; set; }

        public string Username { get; set; }

        [JsonConstructor]
        public AddChatHistory(string role, string text, string username)
        {
            Role = role;
            Text = text;
            Username = username;
        }
    }

    public class SelectionItem
    {
        public int Id { get; set; } // The unique identifier of the selection item.

        public bool Interactive { get; set; } // Whether the selection item is interactive or not.

        public string Text { get; set; } // The content of the selection item.

        public string ImgId { get; set; } // The endpoint of the image of the selection item.

        [JsonConstructor]
        public SelectionItem(int id, bool interactive, string text, string imgId)
        {
            Id = id;
            Interactive = interactive;
            Text = text;
            ImgId = imgId;
        }
    }

    public class ShowTopMenu
    {
        public string Uuid { get; set; } // The unique identifier of the selection group.

        public List<SelectionItem> Items { get; set; } // The selection group. Contains all selection items.

        public bool DestroyLast { get; set; } // Whether the last selection group should be destroyed before the current one is shown.

        [JsonConstructor]
        public ShowTopMenu(string uuid, List<SelectionItem> items, bool destroyLast)
        {
            Uuid = uuid;
            Items = items;
            DestroyLast = destroyLast;
        }
    }
}
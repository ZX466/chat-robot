using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using Cysharp.Threading.Tasks;
using Data;
using JetBrains.Annotations;
using Newtonsoft.Json;
using Service;
using UI;
using UnityEngine;
using UnityEngine.Networking;
using Util;
using Debug = UnityEngine.Debug;
using Object = System.Object;

namespace Web.Api
{
    public enum HttpResponseCode
    {
        Success = 0, // Successful operation
        Failed = 1 // Failed operation
    }

    internal sealed class HttpResponseBody<T>
    {
        public HttpResponseCode Code { get; set; }
        public string Message { get; set; }
        public T Data { get; set; }

        [JsonConstructor]
        public HttpResponseBody(HttpResponseCode code, string message, T data)
        {
            Code = code;
            Message = message;
            Data = data;
        }
    }

    internal class Multipart : IMultipartFormSection
    {
        public string sectionName { get; set; }
        public byte[] sectionData { get; set; }
        public string fileName { get; set; }
        public string contentType { get; set; }
    }

    internal class AudioMetadata
    {
        public int Channels { get; set; }
        public int SampleRate { get; set; }
    }

    public sealed class HttpApi
    {
        private string ServerIp => AppConfigService.Instance.Config.ResourceServer.Host;
        private int ServerPort => AppConfigService.Instance.Config.ResourceServer.Port;
        public static HttpApi Client { get; } = new();


        private List<IMultipartFormSection> CreateMultipartForm(string sectionName, byte[] data,
            string fileName, string contentType)
        {
            return new List<IMultipartFormSection>
            {
                new Multipart
                {
                    sectionName = sectionName,
                    sectionData = data,
                    fileName = fileName,
                    contentType = contentType
                }
            };
        }

        public async UniTask SendCameraImageAsync(byte[] image, FileType fileType)
        {
            Debug.LogFormat($"http://{ServerIp}:{ServerPort}/playground/camera");
            var uri = new Uri($"http://{ServerIp}:{ServerPort}/playground/camera");
            var contentType = fileType switch
            {
                FileType.PNG => "image/png",
                FileType.JPEG => "image/jpeg",
                FileType.JPG => "image/jpg",
                _ => null
            };

            var multipartFormSections = CreateMultipartForm(
                "image", image,
                $"image.{fileType.ToString().ToLower()}",
                contentType);
            using var req = UnityWebRequest.Post(uri, multipartFormSections);
            await req.SendWebRequest();
            if (req.result == UnityWebRequest.Result.Success)
            {
                var responseText = req.downloadHandler.text;
                var response = JsonConverter.DeSerialize<HttpResponseBody<Object>>(responseText);
                if (response.Code == HttpResponseCode.Success)
                {
                    Debug.Log("Sent image to server.");
                }
                else if (response.Code == HttpResponseCode.Failed)
                {
                    Debug.LogErrorFormat("Failed to send image to server: {0}", response.Message);
                }
            }
            else
            {
                ToastLogger.Error($"无法向服务器发送当前拍摄的照片：{req.error}");
                Debug.Log(req.error);
            }
        }

        public async UniTask SendMicrophoneAudioAsync(byte[] audio, FileType fileType, int channels, int sampleRate)
        {
            Debug.LogFormat($"http://{ServerIp}:{ServerPort}/playground/microphone");
            var uri = new Uri($"http://{ServerIp}:{ServerPort}/playground/microphone");

            var contentType = fileType switch
            {
                FileType.WAV => "audio/wav",
                FileType.MP3 => "audio/mp3",
                FileType.OGG => "audio/ogg",
                _ => null
            };

            var jsonString = JsonConverter.Serialize(new AudioMetadata
            {
                Channels = channels,
                SampleRate = sampleRate
            });

            var multipartFormSections = new List<IMultipartFormSection>();
            multipartFormSections.AddRange(CreateMultipartForm(
                "audio", audio,
                $"audio.{fileType.ToString().ToLower()}",
                contentType));
            multipartFormSections.AddRange(CreateMultipartForm(
                "metadata", Encoding.UTF8.GetBytes(jsonString),
                "metadata.json",
                "application/json"));

            using var req = UnityWebRequest.Post(uri, multipartFormSections);
            await req.SendWebRequest();
            if (req.result == UnityWebRequest.Result.Success)
            {
                var responseText = req.downloadHandler.text;
                var response = JsonConverter.DeSerialize<HttpResponseBody<Object>>(responseText);
                if (response.Code == HttpResponseCode.Success)
                {
                    Debug.Log("Sent audio to server.");
                }
                else if (response.Code == HttpResponseCode.Failed)
                {
                    Debug.LogErrorFormat("Failed to send audio to server: {0}", response.Message);
                }
            }
            else
            {
                ToastLogger.Error($"无法向服务器发送当前录制的音频：{req.error}");
                Debug.Log(req.error);
            }
        }

        public async UniTask<Texture2D> GetImageTextureAsync(string fileId)
        {
            // 创建 UriBuilder 对象
            var uriBuilder = new UriBuilder
            {
                Scheme = "http",
                Host = ServerIp,
                Port = ServerPort,
                Path = "/resource/file"
            };

            string encodedFileId = UnityWebRequest.EscapeURL(fileId);
            uriBuilder.Query = $"file_id={encodedFileId}";

            var url = uriBuilder.Uri;
            Debug.LogFormat("GetImageTextureAsync from {0}", url);
            try
            {
                using var www = UnityWebRequestTexture.GetTexture(url);
                await www.SendWebRequest();

                if (www.result == UnityWebRequest.Result.Success)
                {
                    var texture = DownloadHandlerTexture.GetContent(www);
                    return texture;
                }

                throw new Exception($"Failed to download image file: {www.error}");
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                throw;
            }
        }

        public async UniTask<AudioClip> GetAudioClipAsync(string fileId, string audioType)
        {
            // 创建 UriBuilder 对象
            var uriBuilder = new UriBuilder
            {
                Scheme = "http",
                Host = ServerIp,
                Port = ServerPort,
                Path = "/resource/file"
            };

            string encodedFileId = UnityWebRequest.EscapeURL(fileId);
            uriBuilder.Query = $"file_id={encodedFileId}";

            var url = uriBuilder.Uri;
            Debug.LogFormat("GetAudioClipAsync from {0}", url);
            audioType = audioType.ToLower();
            var type = audioType switch
            {
                "wav" => AudioType.WAV,
                "ogg" => AudioType.OGGVORBIS,
                "mp3" => AudioType.MPEG,
                _ => throw new Exception($"Audio type not supported: {audioType}")
            };

            try
            {
                using var www = UnityWebRequestMultimedia.GetAudioClip(url, type);
                await www.SendWebRequest();

                if (www.result == UnityWebRequest.Result.Success)
                {
                    var audioClip = DownloadHandlerAudioClip.GetContent(www);
                    return audioClip;
                }

                ToastLogger.Error($"无法下载音频文件：{www.error}");
                throw new Exception($"Failed to download audio file: {www.error}");
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                throw;
            }
        }

        private async UniTask<byte[]> GetResourceFileAsync(string fileId)
        {
            // 创建 UriBuilder 对象
            var uriBuilder = new UriBuilder
            {
                Scheme = "http",
                Host = ServerIp,
                Port = ServerPort,
                Path = "/resource/file"
            };
            string encodedFileId = UnityWebRequest.EscapeURL(fileId);
            uriBuilder.Query = $"file_id={encodedFileId}";
            var url = uriBuilder.Uri;
            Debug.LogFormat("GetResourceFileAsync from {0}", url);
            using var www = UnityWebRequest.Get(url);
            await www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                var data = www.downloadHandler.data;
                return data;
            }

            ToastLogger.Error($"无法下载 Live2D 文件：{www.error}");
            throw new Exception($"Failed to download Live2D file: {www.error}");
        }

        public async UniTask<string> DownloadResourceFileAsync([NotNull] string fileId,
            FileType fileType = FileType.ZIP,
            bool forceDownload = false)
        {
            var path = Path.Combine(Application.persistentDataPath, fileId + "." + fileType.ToString().ToLower());
            if (forceDownload)
            {
                if (File.Exists(path))
                {
                    Debug.LogFormat("Delete existed file because of force downloading: {0}", path);
                    File.Delete(path);
                }
            }

            if (File.Exists(path))
            {
                Debug.LogFormat("No need to download again, file already exists: {0}", path);
                return path;
            }

            var data = await Client.GetResourceFileAsync(fileId);
            path = await FileUtil.WriteAsync(data, path);
            return path;
        }
    }
}
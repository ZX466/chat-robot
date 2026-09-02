using System;
using System.IO;
using System.IO.Compression;
using Cysharp.Threading.Tasks;
using JetBrains.Annotations;
using UnityEngine;
using UnityEngine.Assertions;
using UnityEngine.Networking;

namespace Util
{
    public static class FileUtil
    {
        public static void TraverseFolders([NotNull] string folderPath, [NotNull] Action<string> callback)
        {
            var subdirectories = Directory.GetDirectories(folderPath);
            var files = Directory.GetFiles(folderPath);

            foreach (var file in files)
            {
                callback(file);
            }

            foreach (var subdirectory in subdirectories)
            {
                TraverseFolders(subdirectory, callback);
            }
        }

        public static string ExtractZipCached(string fileId, string zipFilePath, bool recursive = false)
        {
            var safeId = fileId.Replace(':', '_'); // 与下载缓存一致：Windows 文件名禁 ':'
            var extractDir = Path.Combine(UnityEngine.Application.persistentDataPath, safeId);
            if (Directory.Exists(extractDir))
            {
                Debug.LogFormat("Model directory already exists, skipped: {0}", extractDir);
                return extractDir;
            }

            extractDir = recursive ? RecursiveExtractZipFile(zipFilePath, extractDir) : ExtractZipFile(zipFilePath, extractDir);
            return extractDir;
        }

        public static string RecursiveExtractZipFile(string zipFilePath, string extractPath)
        {
            extractPath = ExtractZipFile(zipFilePath, extractPath);
            Walk(extractPath, file =>
            {
                if (file.EndsWith(".zip"))
                {
                    var directory = file.Remove(file.Length - 4);
                    if (!Directory.Exists(directory))
                    {
                        Directory.CreateDirectory(directory);
                    }

                    ExtractZipFile(file, directory);
                }
            });
            return extractPath;
        }

        /// <summary>
        /// Extract the zip file into a temp directory.
        /// </summary>
        /// <param name="zipFilePath"></param>
        /// <param name="extractPath"></param>
        /// <returns></returns>
        [NotNull]
        public static string ExtractZipFile([NotNull] string zipFilePath, [NotNull] string extractPath)
        {
            if (!File.Exists(zipFilePath))
                throw new FileNotFoundException($"ZIP file not found: {zipFilePath}");

            if (Directory.Exists(extractPath))
            {
                Directory.Delete(extractPath, true);
            }

            Directory.CreateDirectory(extractPath);

            using var archive = ZipFile.OpenRead(zipFilePath);
            var normalizedExtractPath = Path.GetFullPath(extractPath)
                .TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);

            foreach (var entry in archive.Entries)
            {
                if (string.IsNullOrEmpty(entry.FullName))
                    continue;

                var fullPath = Path.GetFullPath(Path.Combine(extractPath, entry.FullName));
                if (!fullPath.StartsWith(normalizedExtractPath + Path.DirectorySeparatorChar) &&
                    !fullPath.StartsWith(normalizedExtractPath + Path.AltDirectorySeparatorChar))
                {
                    Debug.LogError($"[FileUtil] ZipSlip blocked: {entry.FullName}");
                    continue;
                }

                if (entry.FullName.EndsWith("/") || entry.FullName.EndsWith("\\"))
                {
                    Directory.CreateDirectory(fullPath);
                    continue;
                }

                Directory.CreateDirectory(Path.GetDirectoryName(fullPath));
                entry.ExtractToFile(fullPath, overwrite: true);
            }

            return extractPath;
        }


        public static void Walk(string directoryPath, [NotNull] Action<string> callback)
        {
            TraverseFolders(directoryPath, callback);
        }

        /// <summary>
        /// Download file from specific URI using UnityWebRequest.
        /// </summary>
        /// <param name="uri"></param>
        /// <returns>The temp file path.</returns>
        public static async UniTask<string> DownloadFileFromUriAsync(string uri, int timeout = -1)
        {
            Debug.LogFormat("Create request for: {0}", uri);
            var fileExtension = Path.GetExtension(uri);
            var tempFilePath = Path.Combine(UnityEngine.Application.persistentDataPath,
                Guid.NewGuid() + fileExtension.ToLower());

            Assert.IsNotNull(tempFilePath);

            using var request = UnityWebRequest.Get(uri);
            if (timeout > 0)
            {
                request.timeout = timeout;
            }
            await request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"Download failed: {request.error}");
                return null;
            }

            File.WriteAllBytes(tempFilePath, request.downloadHandler.data);
            return tempFilePath;
        }

        public static async UniTask<string> WriteAsync(byte[] data, string path)
        {
            await using var fileStream = new FileStream(path, FileMode.Create);
            await fileStream.WriteAsync(data);
            return path;
        }
    }
}
using System;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;

/// <summary>
/// 团结云开发（DevSecOps / tj-builder）打包构建入口。
/// tj-builder 不指定 buildMethod 时按 Build Settings 直接构建；
/// 此脚本暴露显式构建方法，便于自定义产物路径与失败报错。
/// </summary>
public static class BuildScript
{
    public static void Build()
    {
        var enabledScenes = (EditorBuildSettings.scenes ?? Array.Empty<EditorBuildSettingsScene>())
            .Where(s => s.enabled)
            .Select(s => s.path)
            .ToArray();
        if (enabledScenes.Length == 0)
        {
            throw new InvalidOperationException(
                "No scene enabled in Build Settings. In the Tuanjie/Unity Editor, open " +
                "Assets/Scenes/Main.unity and add it via File > Build Settings (or create your " +
                "own entry scene and register it there).");
        }

        var report = BuildPipeline.BuildPlayer(
            enabledScenes,
            "Builds/zerolan-vtuber.exe",
            BuildTarget.StandaloneWindows64,
            BuildOptions.None);
        if (report.summary.result != BuildResult.Succeeded)
        {
            throw new InvalidOperationException($"Build failed: {report.summary.result}");
        }
    }
}
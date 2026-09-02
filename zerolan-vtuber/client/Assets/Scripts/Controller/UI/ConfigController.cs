using System;
using System.Collections.Generic;
using System.IO;
using Cysharp.Threading.Tasks;
using Data;
using Service;
using TMPro;
using UI;
using UnityEngine;
using UnityEngine.UI;
using Web.Api;

namespace Controller.UI
{
    public class ConfigController : MonoBehaviour
    {
        [SerializeField] private TMP_InputField targetServerInputField;
        [SerializeField] private Button connectButton;
        [SerializeField] private Toggle showUIToggle;
        [SerializeField] private Toggle showSubtitleToggle;
        [SerializeField] private Toggle moveMenuToggle;
        [SerializeField] private Toggle enableARModeToggle;

        // --- 模型服务分区（§12 白名单：供应商配置 UI，key 仅存服务端） ---
        [SerializeField] private TMP_InputField llmBaseUrlInputField;
        [SerializeField] private TMP_InputField llmApiKeyInputField;
        [SerializeField] private TMP_InputField llmModelInputField;
        [SerializeField] private TMP_InputField asrVendorInputField;
        [SerializeField] private TMP_InputField asrBaseUrlInputField;
        [SerializeField] private TMP_InputField asrApiKeyInputField;
        [SerializeField] private TMP_InputField asrModelInputField;
        [SerializeField] private TMP_InputField ttsVendorInputField;
        [SerializeField] private TMP_InputField ttsBaseUrlInputField;
        [SerializeField] private TMP_InputField ttsApiKeyInputField;
        [SerializeField] private TMP_InputField ttsModelInputField;
        [SerializeField] private Button applyProviderConfigButton;
        [SerializeField] private Button quitButton;

        private readonly AppConfigService _appConfigService = AppConfigService.Instance;

        private void Awake()
        {
            AppConfigService.Instance.ConfigPath = Path.Combine(Application.persistentDataPath, "ZerolanPlaygroundConfig.json");
            showUIToggle.onValueChanged.AddListener(TrySyncEnableUIConfig);
            showSubtitleToggle.onValueChanged.AddListener(TrySyncEnableSubtitleConfig);
            moveMenuToggle.onValueChanged.AddListener(TrySyncMenuOnTopConfig);
            enableARModeToggle.onValueChanged.AddListener(TrySyncEnableARModeConfig);
            connectButton.onClick.AddListener(TrySyncServerConfig);
            if (quitButton != null)
            {
                quitButton.onClick.AddListener(() => Application.Quit());
            }
            InitializeProviderConfigUi();
            _appConfigService.LoadConfig().Forget();
        }

        private void TrySyncBoolConfig(bool isOn, System.Func<bool> getter, System.Action<bool> setter)
        {
            if (getter() != isOn)
            {
                setter(isOn);
                _appConfigService.SaveConfig().Forget();
            }
        }

        private void TrySyncEnableUIConfig(bool isOn)
        {
            TrySyncBoolConfig(isOn,
                () => _appConfigService.Config.UIConfig.EnableUI,
                v => _appConfigService.Config.UIConfig.EnableUI = v);
        }

        private void TrySyncEnableSubtitleConfig(bool isOn)
        {
            TrySyncBoolConfig(isOn,
                () => _appConfigService.Config.UIConfig.EnableSubtitle,
                v => _appConfigService.Config.UIConfig.EnableSubtitle = v);
        }

        private void TrySyncMenuOnTopConfig(bool isOn)
        {
            TrySyncBoolConfig(isOn,
                () => _appConfigService.Config.UIConfig.MenuOnTop,
                v => _appConfigService.Config.UIConfig.MenuOnTop = v);
        }

        private void TrySyncEnableARModeConfig(bool isOn)
        {
            TrySyncBoolConfig(isOn,
                () => _appConfigService.Config.DisplayModeConfig.EnableARMode,
                v => _appConfigService.Config.DisplayModeConfig.EnableARMode = v);
        }

        private void TrySyncServerConfig()
        {
            Uri uri = null;
            if (!string.IsNullOrEmpty(targetServerInputField.text))
            {
                try
                {
                    uri = new Uri(targetServerInputField.text);
                }
                catch (Exception e)
                {
                    Debug.LogException(e);
                    Debug.LogError("Can not save config: Error occured while parsing target server URL.");
                    return;
                }
            }

            if (uri != null && uri.Host != _appConfigService.Config.ResourceServer.Host)
            {
                _appConfigService.Config.ResourceServer.Host = uri.Host;
            }

            if (uri != null && uri.Port != _appConfigService.Config.ResourceServer.Port)
            {
                _appConfigService.Config.ResourceServer.Port = uri.Port;
            }

            if (uri != null && uri.Host != _appConfigService.Config.WebSocketServer.Host)
            {
                _appConfigService.Config.WebSocketServer.Host = uri.Host;
            }

            if (uri != null && uri.Port != _appConfigService.Config.WebSocketServer.Port)
            {
                _appConfigService.Config.WebSocketServer.Port = uri.Port;
            }

            if (uri != null)
            {
                _appConfigService.SaveConfig().Forget();
            }
        }

        private void InitializeProviderConfigUi()
        {
            if (llmApiKeyInputField == null || asrVendorInputField == null || ttsVendorInputField == null ||
                applyProviderConfigButton == null)
            {
                return;
            }

            if (llmBaseUrlInputField == null || llmModelInputField == null ||
                asrBaseUrlInputField == null || asrApiKeyInputField == null || asrModelInputField == null ||
                ttsBaseUrlInputField == null || ttsApiKeyInputField == null || ttsModelInputField == null)
            {
                return;
            }

            llmApiKeyInputField.contentType = TMP_InputField.ContentType.Password;
            asrApiKeyInputField.contentType = TMP_InputField.ContentType.Password;
            ttsApiKeyInputField.contentType = TMP_InputField.ContentType.Password;
            applyProviderConfigButton.onClick.AddListener(TryApplyProviderConfig);
        }

        private void TryApplyProviderConfig()
        {
            // §12 约束：api_key 不落盘，仅发送给服务端（key 只存服务端 config.yaml）
            var payload = new Dictionary<string, object>();
            AddNonEmptySlot(payload, "llm", llmBaseUrlInputField, llmApiKeyInputField, llmModelInputField, null);
            AddNonEmptySlot(payload, "asr", asrBaseUrlInputField, asrApiKeyInputField, asrModelInputField,
                asrVendorInputField);
            AddNonEmptySlot(payload, "tts", ttsBaseUrlInputField, ttsApiKeyInputField, ttsModelInputField,
                ttsVendorInputField);

            if (payload.Count == 0)
            {
                ToastLogger.Error("请至少填写一个供应商配置（llm / asr / tts）");
                return;
            }

            if (!ValidateProviderConfig(payload, out var error))
            {
                ToastLogger.Error(error);
                return;
            }

            try
            {
                WsApi.Client.SendAsync(Route.UpdateProviderConfig, payload, "Update provider config");
                ToastLogger.Info("供应商配置已提交，等待服务端确认……");
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                ToastLogger.Error($"提交失败：{e.Message}");
            }
        }

        private static void AddNonEmptySlot(Dictionary<string, object> payload, string slot,
            TMP_InputField baseUrlField, TMP_InputField apiKeyField, TMP_InputField modelField,
            TMP_InputField vendorField)
        {
            if (baseUrlField == null || apiKeyField == null || modelField == null)
            {
                return;
            }

            var slotData = BuildProviderSlot(baseUrlField.text, apiKeyField.text, modelField.text,
                vendorField != null ? vendorField.text : null);
            var baseUrl = (string)slotData["base_url"];
            var apiKey = (string)slotData["api_key"];
            var model = (string)slotData["model"];
            var vendor = slotData.TryGetValue("vendor", out var v) ? (string)v : string.Empty;
            var hasContent = baseUrl.Length > 0 || apiKey.Length > 0 || model.Length > 0 ||
                             (vendor.Length > 0 && apiKey.Length > 0);
            if (hasContent)
            {
                payload[slot] = slotData;
            }
        }

        private static Dictionary<string, object> BuildProviderSlot(string baseUrl, string apiKey, string model,
            string vendor = null)
        {
            var slot = new Dictionary<string, object>
            {
                ["base_url"] = baseUrl.Trim(),
                ["api_key"] = apiKey.Trim(),
                ["model"] = model.Trim(),
            };
            if (!string.IsNullOrEmpty(vendor))
            {
                slot["vendor"] = vendor;
            }

            return slot;
        }

        private static bool ValidateProviderConfig(Dictionary<string, object> payload, out string error)
        {
            error = null;
            foreach (var slot in new[] { "llm", "asr", "tts" })
            {
                if (!payload.TryGetValue(slot, out var raw))
                {
                    continue; // 槽位未填写（可缺省）
                }

                var cfg = (Dictionary<string, object>)raw;
                var baseUrl = (string)cfg["base_url"];
                var apiKey = (string)cfg["api_key"];
                var model = (string)cfg["model"];
                var vendor = cfg.TryGetValue("vendor", out var v) ? (string)v : null;
                var wantsVendor = slot == "asr" || slot == "tts";
                if (string.IsNullOrWhiteSpace(vendor) && wantsVendor)
                {
                    error = $"请选择 {slot} 的 vendor";
                    return false;
                }

                if (string.IsNullOrWhiteSpace(baseUrl) || string.IsNullOrWhiteSpace(apiKey) ||
                    string.IsNullOrWhiteSpace(model))
                {
                    error = $"请完整填写 {slot} 的 base_url / api_key / model";
                    return false;
                }

                if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out var uri) ||
                    (uri.Scheme != "http" && uri.Scheme != "https"))
                {
                    error = $"{slot}.base_url 必须是 http(s) 地址";
                    return false;
                }
            }

            return true;
        }

    }
}
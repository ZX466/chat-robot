using System;
using System.IO;
using Cysharp.Threading.Tasks;
using Service;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

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

        private readonly AppConfigService _appConfigService = AppConfigService.Instance;

        private void Awake()
        {
            AppConfigService.Instance.ConfigPath = Path.Combine(Application.persistentDataPath, "ZerolanPlaygroundConfig.json");
            showUIToggle.onValueChanged.AddListener(TrySyncEnableUIConfig);
            showSubtitleToggle.onValueChanged.AddListener(TrySyncEnableSubtitleConfig);
            moveMenuToggle.onValueChanged.AddListener(TrySyncMenuOnTopConfig);
            enableARModeToggle.onValueChanged.AddListener(TrySyncEnableARModeConfig);
            connectButton.onClick.AddListener(TrySyncServerConfig);
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
        
    }
}
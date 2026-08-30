using Controller;
using Controller.UI;
using Cysharp.Threading.Tasks;
using Data;
using Framework;
using Service;
using UnityEngine;

namespace Handlers
{
    [Handler]
    public class ConnectionHandler : MonoBehaviour
    {
#if VUFORIA_INSTALLED && LIVE2D_SDK_INSTALLED
        [Inject] private CameraController CameraController { get; set; }
#endif
        [Inject] private MicrophoneController MicrophoneController { get; set; }
        [Inject] private UINetworkController UINetworkController { get; set; }
        
        private readonly AppConfigService _appConfigService = AppConfigService.Instance;

        [OnProtocolReceived(Action = Route.ServerHello)]
        private void SetServerConfig(ServerHello serverHello)
        {
            _appConfigService.Config.ResourceServer.Port = serverHello.ResPort;
            _appConfigService.Config.WebSocketServer.Port = serverHello.WsPort;
            _appConfigService.SaveConfig().Forget();

            var wsUri = _appConfigService.GetWebSocketUri();
            UINetworkController.SetAddressTextValue(NetworkConnectionStatus.Connected, wsUri.ToString());
            UINetworkController.StartPing(wsUri.Host);
            
#if VUFORIA_INSTALLED && LIVE2D_SDK_INSTALLED
            CameraController.SwitchToARMode();
#endif
            MicrophoneController.EnableMicrophone();
        }
    }
}
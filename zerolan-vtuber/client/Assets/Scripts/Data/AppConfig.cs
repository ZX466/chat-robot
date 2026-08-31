namespace Data
{
    public class AppConfig
    {
        public ServiceConfig WebSocketServer { get; set; }
        public ServiceConfig ResourceServer { get; set; }
        public UIConfig UIConfig { get; set; }
        public DisplayModeConfig DisplayModeConfig { get; set; }

        public AppConfig(ServiceConfig webSocketServer, ServiceConfig resourceServer, UIConfig uiConfig, DisplayModeConfig displayModeConfig)
        {
            WebSocketServer = webSocketServer;
            ResourceServer = resourceServer;
            UIConfig = uiConfig;
            DisplayModeConfig = displayModeConfig;
        }
    }

    public enum ServiceType
    {
        WebSocket,
        Http
    }

    public class ServiceConfig
    {
        public ServiceType Type { get; set; }
        public string Host { get; set; }
        public int Port { get; set; }

        public ServiceConfig(ServiceType type, string host, int port)
        {
            Type = type;
            Host = host;
            Port = port;
        }
    }

    public class UIConfig
    {
        public bool EnableUI { get; set; }
        public bool EnableSubtitle { get; set; }
        public bool MenuOnTop { get; set; }

        public UIConfig(bool enableUI, bool enableSubtitle, bool menuOnTop)
        {
            EnableUI = enableUI;
            EnableSubtitle = enableSubtitle;
            MenuOnTop = menuOnTop;
        }
    }

    public class DisplayModeConfig
    {
        public bool EnableARMode { get; set; }

        public DisplayModeConfig(bool enableARMode)
        {
            EnableARMode = enableARMode;
        }
    }
}
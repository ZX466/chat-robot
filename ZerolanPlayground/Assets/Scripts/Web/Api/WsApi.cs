namespace Web.Api
{
    public static class WsApi
    {
        public static ZerolanProtocolClient Client { get; private set; } = new();
    }
}
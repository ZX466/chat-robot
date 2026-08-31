using Newtonsoft.Json;

namespace Data
{
    public class ZerolanProtocol<T>
    {
        public string Protocol { get; set; }
        public string Version { get; set; }
        public string Message { get; set; }
        public string Action { get; set; }
        public int Code { get; set; }
        public T Data { get; set; }

        [JsonConstructor]
        public ZerolanProtocol(string protocol, string version, string message, string action, int code, T data)
        {
            Protocol = protocol;
            Version = version;
            Message = message;
            Action = action;
            Code = code;
            Data = data;
        }
    }
}
using System;

namespace Data
{
    public class ModelParamException : Exception
    {
        public override string Message { get; }

        public ModelParamException(string message) : base(message)
        {
            Message = message;
        }
    }
}
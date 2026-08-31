/**
 * @Author: AkagawaTsurunaki
 */

using System;

namespace Framework
{
    /// <summary>
    /// Auto assign to target property with this attribute.
    /// If `GameObjectName` is set, target GameObject with matched name will be set to the property.
    /// If `GameObjectName` is not set, will match with type. Only singleton instance will be used.
    /// </summary>
    [AttributeUsage(AttributeTargets.Property, Inherited = false, AllowMultiple = false)]
    public class Inject : Attribute
    {
        public string GameObjectName { get; set; }
    }

    /// <summary>
    /// Method with `AfterInjected` will be called when properties injection completed.
    /// </summary>
    [AttributeUsage(AttributeTargets.Method, Inherited = false, AllowMultiple = true)]
    public class AfterInjected : Attribute
    {
    }

    /// <summary>
    /// Method with `OnProtocolReceived` will be called when specific action invoked.
    /// </summary>
    [AttributeUsage(AttributeTargets.Method, Inherited = false, AllowMultiple = true)]
    public class OnProtocolReceived : Attribute
    {
        public string Action { get; set; }
    }

    /// <summary>
    /// Class with `Handler` will be automatically instantiated.
    /// Class should inherit `MonoBehaviour`.
    /// </summary>
    [AttributeUsage(AttributeTargets.Class, Inherited = false, AllowMultiple = false)]
    public class Handler : Attribute
    {
    }
}
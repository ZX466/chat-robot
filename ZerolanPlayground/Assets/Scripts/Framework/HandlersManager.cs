using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Cysharp.Threading.Tasks;
using JetBrains.Annotations;
using Unity.VisualScripting;
using UnityEngine;
using Web;
using Web.Api;
using Object = System.Object;

namespace Framework
{
    public class HandlersManager : MonoBehaviour
    {
        private DependencyInjector _dependencyInjector;
        private readonly Dictionary<Type, MonoBehaviour> _handlers = new();
        private static Type[] _cachedHandlerTypes;
        private static readonly object _cacheLock = new();

        public void CreateHandlers(DependencyInjector dependencyInjector)
        {
            _dependencyInjector = dependencyInjector;
            InstantiateHandlers();
            InjectDependencies();
            CallAfterInjected();
            foreach (var (type, monoBehaviour) in _handlers)
            {
                ScanMethods(monoBehaviour);
            }
        }

        public void DestroyHandlers()
        {
            foreach (var (type, monoBehaviour) in _handlers)
            {
                DestroyImmediate(monoBehaviour);
            }
            _handlers.Clear();
        }

        private void InjectDependencies()
        {
            foreach (var kv in _handlers)
            {
                _dependencyInjector.InjectDependencies(kv.Value);
            }
        }

        /// <summary>
        /// After dependencies are injected to the instance, call the methods with attribute [AfterInjected]
        /// </summary>
        private void CallAfterInjected()
        {
            foreach (var kv in _handlers)
            {
                var instance = kv.Value;
                var type = instance.GetType();
                foreach (var methodInfo in type.GetMethods(BindingFlags.NonPublic | BindingFlags.Public |
                                                           BindingFlags.Instance | BindingFlags.Static))
                {
                    if (methodInfo.GetAttribute<AfterInjected>() != null)
                    {
                        try
                        {
                            methodInfo.Invoke(instance, null);
                        }
                        catch (Exception e)
                        {
                            Debug.LogError($"Exception in [AfterInjected] method {type.Name}.{methodInfo.Name}: {e}");
                        }
                    }
                }
            }
        }

        private void InstantiateHandlers()
        {
            lock (_cacheLock)
            {
                if (_cachedHandlerTypes == null)
                {
                    var assembly = Assembly.GetExecutingAssembly();
                    _cachedHandlerTypes = assembly.GetTypes()
                        .Where(t => t.GetCustomAttributes(typeof(Handler), false).Length > 0
                                    && typeof(MonoBehaviour).IsAssignableFrom(t))
                        .ToArray();
                }
            }

            foreach (var type in _cachedHandlerTypes)
            {
                var methodInfo = gameObject.GetType().GetMethod("AddComponent",
                    BindingFlags.Instance | BindingFlags.Public, null,
                    CallingConventions.HasThis | CallingConventions.ExplicitThis, new[] { typeof(Type) },
                    null);
                var component = methodInfo?.Invoke(gameObject, new object[] { type }) as Component;
                Debug.LogFormat("Handler `{0}` is instantiated.", type.Name);
                _handlers.Add(type, component as MonoBehaviour);
            }
        }


        private static void ScanMethods(Object obj)
        {
            var type = obj.GetType();
            var methods = type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic |
                                          BindingFlags.Instance | BindingFlags.DeclaredOnly);
            var registeredActions = new HashSet<string>();
            foreach (var method in methods)
            {
                var onEventAttribute = method.GetCustomAttribute<OnProtocolReceived>();
                if (onEventAttribute != null)
                {
                    var actionKey = $"{type.FullName}.{onEventAttribute.Action}";
                    if (!registeredActions.Add(actionKey))
                    {
                        Debug.LogWarning($"Duplicate listener skipped: {method.Name} for action {onEventAttribute.Action}");
                        continue;
                    }
                    var parameterInfos = method.GetParameters();
                    var cachedAction = CreateInvoker(obj, method, parameterInfos);
                    WsApi.Client.AddOnMessage<Object>(onEventAttribute.Action,
                        data =>
                        {
                            if (data != null)
                            {
                                if (parameterInfos.Length != 1)
                                {
                                    throw new ArgumentException("Method must have exactly one parameter.");
                                }

                                var protocolData = JsonConverter.DeserializeByType(data.ToString(),
                                    parameterInfos[0].ParameterType);
                                cachedAction(protocolData);
                            }
                            else
                            {
                                cachedAction(null);
                            }
                        });
                    Debug.LogFormat("Listener `{0}` is registered.", method.Name);
                }
            }
        }

        private static Action<object> CreateInvoker(Object obj, MethodInfo methodInfo, ParameterInfo[] parameterInfos)
        {
            var behaviour = obj as MonoBehaviour;
            var isCoroutine = methodInfo.ReturnType == typeof(IEnumerator);

            return data =>
            {
                var args = data != null ? new[] { data } : null;
                if (isCoroutine)
                {
                    // CRITICAL-1: WebSocket callbacks may arrive on worker threads.
                    // StartCoroutine must be called on the main thread.
                    _ = InvokeOnMainThread(behaviour, () => methodInfo.Invoke(obj, args) as IEnumerator);
                }
                else
                {
                    methodInfo.Invoke(obj, args);
                }
            };
        }

        private static async UniTaskVoid InvokeOnMainThread(MonoBehaviour behaviour, Func<IEnumerator> coroutineFactory)
        {
            await UniTask.SwitchToMainThread();
            behaviour.StartCoroutine(coroutineFactory());
        }
    }
}
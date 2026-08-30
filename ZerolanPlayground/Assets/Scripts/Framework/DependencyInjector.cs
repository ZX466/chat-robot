/**
 * @Author: AkagawaTsurunaki
 */
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Unity.VisualScripting;
using UnityEngine;

namespace Framework
{
    public class DependencyInjectException : Exception
    {
        public DependencyInjectException(string msg) : base(msg)
        {
        }
    }

    public class DependencyInjector : MonoBehaviour
    {
        public Dictionary<Type, object> Dependencies { get; } = new();
        private Dictionary<string, List<GameObject>> _gameObjectCache;

        private void BuildGameObjectCache()
        {
            _gameObjectCache = new Dictionary<string, List<GameObject>>();
            var allGameObjects = FindObjectsOfType<GameObject>();
            foreach (var go in allGameObjects)
            {
                if (!_gameObjectCache.TryGetValue(go.name, out var list))
                {
                    list = new List<GameObject>();
                    _gameObjectCache[go.name] = list;
                }

                list.Add(go);
            }
        }

        private List<GameObject> FindGameObjectsByName(string name)
        {
            if (_gameObjectCache == null)
            {
                BuildGameObjectCache();
            }

            return _gameObjectCache.TryGetValue(name, out var result) ? result : new List<GameObject>();
        }

        private bool InjectGameObject(MonoBehaviour target, PropertyInfo property)
        {
            var attribute = property.GetAttribute<Inject>();
            if (attribute.GameObjectName != null)
            {
                var goList = FindGameObjectsByName(attribute.GameObjectName);
                if (goList == null)
                {
                    throw new DependencyInjectException($"Could not find GameObject: {attribute.GameObjectName}");
                }

                if (goList.Count != 1)
                {
                    throw new DependencyInjectException(
                        $"Too many GameObject ({goList.Count}): {attribute.GameObjectName}");
                }

                var component = goList[0].GetComponent(property.PropertyType);
                if (component == null)
                {
                    throw new DependencyInjectException(
                        $"GameObject {attribute.GameObjectName} is found but there is no component {property.PropertyType} attached");
                }

                property.SetValue(target, component);
                return true;
            }

            return false;
        }

        private bool InjectOthers(MonoBehaviour target, PropertyInfo property)
        {
            var propertyType = property.PropertyType;
            if (!Dependencies.TryGetValue(propertyType, out var dependency) || dependency == null)
            {
                throw new NullReferenceException($"Dependency property {property.Name} has not been set.");
            }

            try
            {
                property.SetValue(target, dependency);
                return true;
            }
            catch (ArgumentException e)
            {
                if (e.Message.Contains("Set Method not found"))
                {
                    Debug.LogError(
                        $"Dependency property {property.Name} has not been set because this property has no set method.");
                }

                throw;
            }
        }

        public void InjectDependencies(MonoBehaviour target)
        {
            var targetType = target.GetType();
            var properties = targetType
                .GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                .Where(p => p.GetCustomAttribute<Inject>() != null)
                .ToArray();

            foreach (var property in properties)
            {
                if (InjectGameObject(target, property))
                {
                    continue;
                }

                InjectOthers(target, property);
            }
        }
    }
}
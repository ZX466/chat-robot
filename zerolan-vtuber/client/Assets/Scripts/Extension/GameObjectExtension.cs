using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Extension
{
    public static class GameObjectExtension
    {
        // 递归获取指定组件
        public static List<T> GetComponentsInChildrenRecursive<T>(this GameObject root, bool includeInactive = false)
            where T : Component
        {
            // 获取当前游戏对象的所有指定组件
            var currentComponents = root.GetComponents<T>();
            var components = currentComponents.ToList();

            // 遍历所有子游戏对象
            foreach (Transform child in root.transform)
            {
                // 递归调用
                components.AddRange(GetComponentsInChildrenRecursive<T>(child.gameObject, includeInactive));
            }

            return components;
        }
    }
}
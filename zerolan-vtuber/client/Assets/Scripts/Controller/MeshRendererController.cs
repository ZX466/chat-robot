using System.Linq;
using Extension;
using UnityEngine;
using Util;

namespace Controller
{
    public class MeshRendererController : MonoBehaviour
    {
        public Rectangle GetBounds()
        {
            var meshRenderers = gameObject.GetComponentsInChildren<MeshRenderer>(includeInactive: true);
            var circles = meshRenderers.Select(meshRenderer => new Circle()
            {
                X = meshRenderer.bounds.center.x,
                Y = meshRenderer.bounds.center.y,
                Radius = meshRenderer.bounds.extents.magnitude
            }).ToList();

            var rectangle = BoundsUtil.CalculateBoundingRectangle(circles);
            return rectangle;
        }

        private void OnDrawGizmosSelected()
        {
            var rectangle = GetBounds();
            Gizmos.color = Color.yellow;
            // 计算矩形的中心点
            var rectCenter = new Vector3((float)(rectangle.Left + rectangle.Right) / 2,
                (float)(rectangle.Bottom + rectangle.Top) / 2, 0);

            // 计算矩形的宽度和高度
            float width = (float)(rectangle.Right - rectangle.Left);
            float height = (float)(rectangle.Top - rectangle.Bottom);

            Gizmos.DrawWireCube(rectCenter, new Vector3(width, height, 0.1f));
        }
    }
}
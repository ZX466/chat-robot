using UnityEngine;
using Util;

namespace Controller
{
    public class SmartCamera : MonoBehaviour
    {
        private Camera _camera;

        private void Awake()
        {
            _camera = gameObject.GetComponent<Camera>();
        }

        public void AdjustCameraToFitRectangle(Rectangle rectangle)
        {
            // 计算矩形的中心点
            var rectangleCenter = new Vector3((float)(rectangle.Left + rectangle.Right) / 2,
                (float)(rectangle.Bottom + rectangle.Top) / 2, 0);

            // 计算矩形的宽度和高度
            var rectangleWidth = (float)(rectangle.Right - rectangle.Left);
            var rectangleHeight = (float)(rectangle.Top - rectangle.Bottom);

            // 计算相机的位置
            var cameraPosition = CalculateCameraPosition(rectangleCenter, rectangleWidth, rectangleHeight);

            // 设置相机的位置
            _camera.transform.position = cameraPosition;

            // 设置相机的视野以适应矩形
            AdjustCameraFieldOfView(rectangleHeight);
        }

        private Vector3 CalculateCameraPosition(Vector3 rectangleCenter, float rectangleWidth, float rectangleHeight)
        {
            // 计算相机与矩形之间的距离
            var distance = Mathf.Max(
                rectangleWidth / 2 / Mathf.Tan(_camera.fieldOfView * 0.5f * Mathf.Deg2Rad),
                rectangleHeight / 2 / Mathf.Tan(_camera.fieldOfView * 0.5f * Mathf.Deg2Rad));

            // 计算相机的位置
            return rectangleCenter + new Vector3(0, 0, -distance);
        }

        private void AdjustCameraFieldOfView(float rectangleHeight)
        {
            // 计算新的视野以适应矩形高度
            var newFieldOfView =
                2 * Mathf.Atan(rectangleHeight / 2 /
                               Vector3.Distance(_camera.transform.position, new Vector3(0, 0, 0))) *
                Mathf.Rad2Deg;
            _camera.fieldOfView = newFieldOfView;
        }
    }
}
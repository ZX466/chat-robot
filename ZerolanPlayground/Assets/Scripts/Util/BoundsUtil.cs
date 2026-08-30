using System;
using System.Collections.Generic;

namespace Util
{
    public sealed class Circle
    {
        public double X { get; set; } // 圆心的X坐标
        public double Y { get; set; } // 圆心的Y坐标
        public double Radius { get; set; } // 圆的半径
    }

    public sealed class Rectangle
    {
        public double Left { get; set; } // 矩形的左边
        public double Right { get; set; } // 矩形的右边
        public double Top { get; set; } // 矩形的上边
        public double Bottom { get; set; } // 矩形的下边
    }

    public static class BoundsUtil
    {
        public static Rectangle CalculateBoundingRectangle(List<Circle> circles)
        {
            if (circles == null || circles.Count == 0)
                throw new ArgumentException("圆列表不能为空");

            // 初始化边界为第一个圆的外接矩形
            var left = circles[0].X - circles[0].Radius;
            var right = circles[0].X + circles[0].Radius;
            var top = circles[0].Y + circles[0].Radius;
            var bottom = circles[0].Y - circles[0].Radius;

            // 遍历所有圆，找到最左边、最右边、最上边和最下边的点
            for (int i = 1; i < circles.Count; i++)
            {
                var circle = circles[i];
                var circleLeft = circle.X - circle.Radius;
                var circleRight = circle.X + circle.Radius;
                var circleTop = circle.Y + circle.Radius;
                var circleBottom = circle.Y - circle.Radius;

                if (circleLeft < left)
                    left = circleLeft;
                if (circleRight > right)
                    right = circleRight;
                if (circleTop > top)
                    top = circleTop;
                if (circleBottom < bottom)
                    bottom = circleBottom;
            }

            return new Rectangle { Left = left, Right = right, Top = top, Bottom = bottom };
        }
    }
}
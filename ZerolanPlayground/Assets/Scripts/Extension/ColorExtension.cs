using UnityEngine;

namespace Extension
{
    public static class ColorExtension
    {
        public static Color FromString(this Color self, string color)
        {
            if (color == null) return self;
            if (!ColorUtility.TryParseHtmlString(color, out var result))
            {
                result = self;
            }

            return result;
        }
    }
}
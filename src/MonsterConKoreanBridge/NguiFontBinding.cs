using UnityEngine;

namespace MonsterConKoreanBridge
{
    internal static class NguiFontBinding
    {
        // NGUI needs invalidation only when the font actually changes. Avoid
        // reflection and geometry invalidation during typewriter text updates.
        internal static bool Apply(UILabel label, Font font)
        {
            if (label.trueTypeFont == font && label.font == null) return false;
            label.SetTrueTypeFont(font);
            label.MarkAsChanged();
            return true;
        }
    }
}

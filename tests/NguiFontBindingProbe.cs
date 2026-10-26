using System;

// Test doubles for counting font changes without starting Unity or the game.
namespace UnityEngine { public class Font { } }
public class UILabel
{
    public UnityEngine.Font trueTypeFont;
    public object font;
    public int Assignments, Rebuilds;
    public void SetTrueTypeFont(UnityEngine.Font value)
    {
        trueTypeFont = value;
        font = null;
        Assignments++;
    }
    public void MarkAsChanged() { Rebuilds++; }
}

public static class NguiFontBindingProbe
{
    public static int Main()
    {
        var desired = new UnityEngine.Font();
        var label = new UILabel { font = new object() };
        for (int update = 0; update < 20000; update++)
            MonsterConKoreanBridge.NguiFontBinding.Apply(label, desired);
        if (label.Assignments != 1 || label.Rebuilds != 1)
            throw new Exception("Repeated text updates rebuilt an unchanged font");
        label.font = new object();
        MonsterConKoreanBridge.NguiFontBinding.Apply(label, desired);
        if (label.Rebuilds != 2 || label.font != null)
            throw new Exception("Restored bitmap font was not repaired");
        label.trueTypeFont = new UnityEngine.Font();
        MonsterConKoreanBridge.NguiFontBinding.Apply(label, desired);
        if (label.Rebuilds != 3 || label.trueTypeFont != desired)
            throw new Exception("Foreign font was not repaired");
        Console.WriteLine("PASS 20000 repeated calls: one initial font change; bitmap/foreign font repairs preserved");
        return 0;
    }
}

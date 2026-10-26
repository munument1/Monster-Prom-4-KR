using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using HarmonyLib;
using MonsterConKoreanBridge;

// No Unity types or game instances are created by this test.
public class UILabel { public string text { get; set; } }

public static class StatNameLocalizationProbe
{
    public static int Main()
    {
        string[] names = { "SMARTS", "BOLDNESS", "CREATIVITY", "CHARM", "FUN", "MONEY" };
        string[] translated = { "지능", "대담함", "창의력", "매력", "재미", "돈" };
        for (int i = 0; i < names.Length; i++)
            if (StatNameLocalization.Translate(names[i]) != translated[i]) throw new Exception("Wrong stat translation");
        if (StatNameLocalization.Translate(null) != null || StatNameLocalization.Translate("13") != "13" ||
            StatNameLocalization.Translate("CUSTOM_STAT") != "CUSTOM_STAT") throw new Exception("Unexpected non-stat change");
        MethodInfo setter = typeof(UILabel).GetProperty("text").GetSetMethod();
        var method = new DynamicMethod("fixture", typeof(void), Type.EmptyTypes);
        Label entry = method.GetILGenerator().DefineLabel();
        var set = new CodeInstruction(OpCodes.Callvirt, setter);
        set.labels.Add(entry);
        var original = new List<CodeInstruction> { new CodeInstruction(OpCodes.Ldstr, "SMARTS"), set, new CodeInstruction(OpCodes.Ret) };
        var patched = StatNameLocalization.Transpile(original).ToList();
        if (patched.Count != 4 || patched[1].opcode != OpCodes.Call ||
            ((MethodInfo)patched[1].operand).Name != "Translate" || patched[2] != set ||
            patched[1].labels.Count != 1 || patched[2].labels.Count != 0) throw new Exception("Incorrect insertion or branch target");
        bool failed = false;
        try { StatNameLocalization.Transpile(new[] { new CodeInstruction(OpCodes.Ret) }); }
        catch (InvalidOperationException) { failed = true; }
        if (!failed) throw new Exception("Missing setter was silently accepted");
        // Execute transformed IL against a tiny label fixture. This checks the
        // actual evaluation stack and call accessibility without loading Unity.
        var assignment = new DynamicMethod("assign", typeof(void), new[] { typeof(UILabel) }, typeof(StatNameLocalizationProbe).Module, true);
        ILGenerator il = assignment.GetILGenerator();
        il.Emit(OpCodes.Ldarg_0);
        il.Emit(OpCodes.Ldstr, "SMARTS");
        il.Emit(OpCodes.Call, (MethodInfo)patched[1].operand);
        il.Emit(OpCodes.Callvirt, setter);
        il.Emit(OpCodes.Ret);
        var assign = (Action<UILabel>)assignment.CreateDelegate(typeof(Action<UILabel>));
        var label = new UILabel();
        assign(label);
        if (label.text != "지능") throw new Exception("Generated assignment did not localize");
        Console.WriteLine("PASS six stat names; numeric/custom labels unchanged; pre-setter IL insertion/branch/stack checked.");
        return 0;
    }
}

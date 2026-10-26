using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using HarmonyLib;
using MonsterConKoreanBridge;

// No Unity types or game instances are created by this test.
public class UILabel { public string text { get; set; } }
namespace BeautifulGlitchConfig { public enum StatType { Smarts, Boldness, Creativity, Charm, Fun } }

public static class StatNameLocalizationProbe
{
    public static int Main()
    {
        string[] names = { "SMARTS", "BOLDNESS", "CREATIVITY", "CHARM", "FUN", "MONEY" };
        string[] translated = { "지능", "대담함", "창의력", "매력", "재미", "돈" };
        for (int i = 0; i < names.Length; i++)
        {
            string titleCase = names[i].Substring(0, 1) + names[i].Substring(1).ToLowerInvariant();
            if (StatNameLocalization.Translate(names[i]) != translated[i] ||
                StatNameLocalization.Translate(titleCase) != translated[i] ||
                StatNameLocalization.Translate(names[i].ToLowerInvariant()) != translated[i] ||
                StatNameLocalization.TranslateStatText("STA_" + names[i]) != translated[i]) throw new Exception("Wrong stat translation/casing");
        }
        if (StatNameLocalization.TranslateStatText("STA_CUSTOM") != "STA_CUSTOM") throw new Exception("Unknown stat key changed");
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
        VerifyDialogueFormatting(names, translated);
        VerifyPauseSheet(setter);
        Console.WriteLine("PASS six stat names; numeric/custom labels unchanged; pre-setter IL insertion/branch/stack checked.");
        return 0;
    }

    private static void VerifyPauseSheet(MethodInfo setter)
    {
        var display = new DynamicMethod("pauseStats", typeof(void), new[] { typeof(UILabel) }, typeof(StatNameLocalizationProbe).Module, true);
        ILGenerator il = display.GetILGenerator();
        LocalBuilder stat = il.DeclareLocal(typeof(BeautifulGlitchConfig.StatType));
        var source = new List<CodeInstruction> {
            // An unrelated name and a numeric string must remain untouched.
            new CodeInstruction(OpCodes.Ldarg_0), new CodeInstruction(OpCodes.Ldstr, "Smarts"), new CodeInstruction(OpCodes.Callvirt, setter),
            new CodeInstruction(OpCodes.Ldarg_0), new CodeInstruction(OpCodes.Ldstr, "15"), new CodeInstruction(OpCodes.Callvirt, setter),
            new CodeInstruction(OpCodes.Ldc_I4_0), new CodeInstruction(OpCodes.Stloc, stat),
            new CodeInstruction(OpCodes.Ldarg_0), new CodeInstruction(OpCodes.Ldloca, stat),
            new CodeInstruction(OpCodes.Constrained, typeof(BeautifulGlitchConfig.StatType)),
            new CodeInstruction(OpCodes.Callvirt, typeof(object).GetMethod("ToString")),
            new CodeInstruction(OpCodes.Callvirt, setter), new CodeInstruction(OpCodes.Ret)
        };
        var patched = StatNameLocalization.TranspilePauseStats(source).ToList();
        if (patched.Count != source.Count + 1 || patched[2] != source[2] || patched[5] != source[5] || patched[12].opcode != OpCodes.Call)
            throw new Exception("Pause patch changed unrelated labels");
        foreach (CodeInstruction instruction in patched)
        {
            if (instruction.operand == null) il.Emit(instruction.opcode);
            else if (instruction.operand is string) il.Emit(instruction.opcode, (string)instruction.operand);
            else if (instruction.operand is Type) il.Emit(instruction.opcode, (Type)instruction.operand);
            else if (instruction.operand is MethodInfo) il.Emit(instruction.opcode, (MethodInfo)instruction.operand);
            else if (instruction.operand is LocalBuilder) il.Emit(instruction.opcode, (LocalBuilder)instruction.operand);
            else throw new Exception("Unexpected pause fixture operand");
        }
        var assign = (Action<UILabel>)display.CreateDelegate(typeof(Action<UILabel>));
        var label = new UILabel();
        assign(label);
        if (label.text != "지능") throw new Exception("Pause enum display did not translate TitleCase");
        Console.WriteLine("PASS pause-menu enum display and all upper/title/lower stat cases; unrelated labels unchanged.");
    }

    private static void VerifyDialogueFormatting(string[] names, string[] translated)
    {
        var display = new DynamicMethod("display", typeof(string), new[] { typeof(string), typeof(string), typeof(string), typeof(uint) }, typeof(StatNameLocalizationProbe).Module, true);
        ILGenerator il = display.GetILGenerator();
        LocalBuilder localName = il.DeclareLocal(typeof(string));
        var source = new List<CodeInstruction> {
            new CodeInstruction(OpCodes.Ldarg_0), new CodeInstruction(OpCodes.Stloc, localName),
            new CodeInstruction(OpCodes.Ldstr, "{0}{1}{2}{3}{4}[-]"),
            new CodeInstruction(OpCodes.Ldc_I4_5), new CodeInstruction(OpCodes.Newarr, typeof(object)),
            new CodeInstruction(OpCodes.Dup), new CodeInstruction(OpCodes.Ldc_I4_0), new CodeInstruction(OpCodes.Ldarg_1), new CodeInstruction(OpCodes.Stelem_Ref),
            new CodeInstruction(OpCodes.Dup), new CodeInstruction(OpCodes.Ldc_I4_1), new CodeInstruction(OpCodes.Ldarg_2), new CodeInstruction(OpCodes.Stelem_Ref),
            new CodeInstruction(OpCodes.Dup), new CodeInstruction(OpCodes.Ldc_I4_2), new CodeInstruction(OpCodes.Ldarg_3), new CodeInstruction(OpCodes.Box, typeof(uint)), new CodeInstruction(OpCodes.Stelem_Ref),
            new CodeInstruction(OpCodes.Dup), new CodeInstruction(OpCodes.Ldc_I4_3), new CodeInstruction(OpCodes.Ldstr, " "), new CodeInstruction(OpCodes.Stelem_Ref),
            new CodeInstruction(OpCodes.Dup), new CodeInstruction(OpCodes.Ldc_I4_4), new CodeInstruction(OpCodes.Ldloc, localName), new CodeInstruction(OpCodes.Stelem_Ref),
            new CodeInstruction(OpCodes.Call, typeof(string).GetMethod("Format", new[] { typeof(string), typeof(object[]) })), new CodeInstruction(OpCodes.Ret)
        };
        var patched = StatNameLocalization.TranspileDialogueStats(source).ToList();
        if (patched.Count != source.Count + 1) throw new Exception("Dialogue patch must insert exactly one call");
        foreach (CodeInstruction instruction in patched)
        {
            if (instruction.operand == null) il.Emit(instruction.opcode);
            else if (instruction.operand is string) il.Emit(instruction.opcode, (string)instruction.operand);
            else if (instruction.operand is Type) il.Emit(instruction.opcode, (Type)instruction.operand);
            else if (instruction.operand is MethodInfo) il.Emit(instruction.opcode, (MethodInfo)instruction.operand);
            else if (instruction.operand is LocalBuilder) il.Emit(instruction.opcode, (LocalBuilder)instruction.operand);
            else throw new Exception("Unexpected fixture operand");
        }
        var format = (Func<string, string, string, uint, string>)display.CreateDelegate(typeof(Func<string, string, string, uint, string>));
        for (int i = 0; i < names.Length; i++)
        {
            if (format(names[i], "[00FFFF]", "+", 2) != "[00FFFF]+2 " + translated[i] + "[-]") throw new Exception("Positive dialogue stat changed amount/color");
            if (format(names[i], "[FF0000]", "-", 13) != "[FF0000]-13 " + translated[i] + "[-]") throw new Exception("Negative dialogue stat changed amount/color");
        }
        if (format("금덩이", "[00FFFF]", "+", 99) != "[00FFFF]+99 금덩이[-]" ||
            format("FAKE_STAT", "[00FFFF]", "+", 3) != "[00FFFF]+3 FAKE_STAT[-]") throw new Exception("Custom stat name changed");
        bool failed = false;
        try { StatNameLocalization.TranspileDialogueStats(new[] { new CodeInstruction(OpCodes.Ret) }); }
        catch (InvalidOperationException) { failed = true; }
        if (!failed) throw new Exception("Missing dialogue display slot was silently accepted");
        Console.WriteLine("PASS dialogue stats: six names, positive/negative amounts, color/reset tags and custom names preserved; generated IL executed without Unity.");
    }
}

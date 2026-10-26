using System;
using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using HarmonyLib;

namespace MonsterConKoreanBridge
{
    // Only the strings assigned to StatWidget.nameLabel are localized.
    // StatType enum names remain intact for event parsing and saved games.
    internal static class StatNameLocalization
    {
        internal static string Translate(string name)
        {
            switch (name)
            {
                case "SMARTS": case "Smarts": case "smarts": return "지능";
                case "BOLDNESS": case "Boldness": case "boldness": return "대담함";
                case "CREATIVITY": case "Creativity": case "creativity": return "창의력";
                case "CHARM": case "Charm": case "charm": return "매력";
                case "FUN": case "Fun": case "fun": return "재미";
                case "MONEY": case "Money": case "money": return "돈";
                default: return name;
            }
        }

        internal static string TranslateStatText(string text)
        {
            if (text == null || !text.StartsWith("STA_", StringComparison.Ordinal)) return Translate(text);
            string name = text.Substring(4);
            string translated = Translate(name);
            return translated == name ? text : translated;
        }

        internal static IEnumerable<CodeInstruction> TranspilePauseStats(IEnumerable<CodeInstruction> instructions)
        {
            var result = new List<CodeInstruction>(instructions);
            MethodInfo translate = typeof(StatNameLocalization).GetMethod("Translate", BindingFlags.Static | BindingFlags.NonPublic);
            int replaced = 0;
            for (int index = 2; index < result.Count; index++)
            {
                MethodInfo setter = result[index].operand as MethodInfo;
                MethodInfo toString = result[index - 1].operand as MethodInfo;
                Type constrained = result[index - 2].operand as Type;
                if (result[index].opcode != OpCodes.Callvirt || setter == null ||
                    setter.DeclaringType.FullName != "UILabel" || setter.Name != "set_text" ||
                    toString == null || toString.DeclaringType != typeof(object) || toString.Name != "ToString" ||
                    result[index - 2].opcode != OpCodes.Constrained || constrained == null ||
                    constrained.FullName != "BeautifulGlitchConfig.StatType") continue;
                var call = new CodeInstruction(OpCodes.Call, translate);
                call.labels.AddRange(result[index].labels);
                result[index].labels.Clear();
                result.Insert(index, call);
                index++;
                replaced++;
            }
            if (replaced != 1)
                throw new InvalidOperationException("Expected exactly one pause-menu stat-name assignment; found " + replaced + ".");
            return result;
        }

        internal static IEnumerable<CodeInstruction> Transpile(IEnumerable<CodeInstruction> instructions)
        {
            var result = new List<CodeInstruction>();
            MethodInfo translate = typeof(StatNameLocalization).GetMethod("Translate", BindingFlags.Static | BindingFlags.NonPublic);
            int replaced = 0;
            foreach (CodeInstruction instruction in instructions)
            {
                MethodInfo method = instruction.operand as MethodInfo;
                if (instruction.opcode == OpCodes.Callvirt && method != null &&
                    method.DeclaringType.FullName == "UILabel" && method.Name == "set_text")
                {
                    // AwakeMe sets the name before measuring/cloning the labels.
                    // Insert here so the animated auxiliary copies inherit Korean.
                    var call = new CodeInstruction(OpCodes.Call, translate);
                    call.labels.AddRange(instruction.labels);
                    instruction.labels.Clear();
                    result.Add(call);
                    replaced++;
                }
                result.Add(instruction);
            }
            if (replaced != 1)
                throw new InvalidOperationException("Expected exactly one stat-name label assignment in StatWidget.AwakeMe; found " + replaced + ".");
            return result;
        }

        internal static IEnumerable<CodeInstruction> TranspileDialogueStats(IEnumerable<CodeInstruction> instructions)
        {
            var result = new List<CodeInstruction>(instructions);
            MethodInfo translate = typeof(StatNameLocalization).GetMethod("Translate", BindingFlags.Static | BindingFlags.NonPublic);
            bool inDisplayFormat = false;
            int replaced = 0;
            for (int index = 0; index < result.Count; index++)
            {
                CodeInstruction instruction = result[index];
                if (instruction.opcode == OpCodes.Ldstr && (string)instruction.operand == "{0}{1}{2}{3}{4}[-]")
                    inDisplayFormat = true;
                if (!inDisplayFormat) continue;
                MethodInfo method = instruction.operand as MethodInfo;
                if (method != null && method.DeclaringType == typeof(string) && method.Name == "Format")
                {
                    inDisplayFormat = false;
                    continue;
                }
                // Slot 4 is only the display name, after the stat has already
                // been parsed and its numeric StatChange added to the result.
                if (instruction.opcode == OpCodes.Ldc_I4_4 && index + 2 < result.Count &&
                    result[index + 1].IsLdloc() && result[index + 2].opcode == OpCodes.Stelem_Ref)
                {
                    CodeInstruction store = result[index + 2];
                    var call = new CodeInstruction(OpCodes.Call, translate);
                    call.labels.AddRange(store.labels);
                    store.labels.Clear();
                    result.Insert(index + 2, call);
                    index += 3;
                    replaced++;
                }
            }
            if (replaced != 1)
                throw new InvalidOperationException("Expected exactly one dialogue stat display-name slot; found " + replaced + ".");
            return result;
        }
    }
}

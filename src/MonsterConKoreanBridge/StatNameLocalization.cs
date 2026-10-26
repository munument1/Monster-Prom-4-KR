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
                case "SMARTS": return "지능";
                case "BOLDNESS": return "대담함";
                case "CREATIVITY": return "창의력";
                case "CHARM": return "매력";
                case "FUN": return "재미";
                case "MONEY": return "돈";
                default: return name;
            }
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
    }
}

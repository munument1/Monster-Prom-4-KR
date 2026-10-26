using System;
using System.Collections.Generic;
using System.Reflection.Emit;
using System.Xml;
using HarmonyLib;

namespace MonsterConKoreanBridge
{
    internal static class SaveNameSerializationPatch
    {
        internal static IEnumerable<CodeInstruction> Transpile(IEnumerable<CodeInstruction> instructions)
        {
            var original = AccessTools.Method(typeof(XmlWriter), "WriteElementString", new[] { typeof(string), typeof(string) });
            var replacement = AccessTools.Method(typeof(SaveNameEncoding), "WriteElementString");
            var result = new List<CodeInstruction>();
            int replaced = 0;
            foreach (CodeInstruction instruction in instructions)
            {
                if (instruction.Calls(original))
                {
                    // The wrapper emits Unicode entities only for Name; all
                    // other fields keep the original writer call and values.
                    instruction.opcode = OpCodes.Call;
                    instruction.operand = replacement;
                    replaced++;
                }
                result.Add(instruction);
            }
            if (replaced == 0)
                throw new InvalidOperationException("No player XML string writes found; Unicode name protection was not installed.");
            return result;
        }
    }
}

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using System.Text;
using System.Xml;
using HarmonyLib;
using MonsterConKoreanBridge;

internal static class SaveNameTranspilerProbe
{
    public static void Main()
    {
        MethodInfo original = typeof(XmlWriter).GetMethod("WriteElementString", new[] { typeof(string), typeof(string) });
        var source = new List<CodeInstruction> {
            new CodeInstruction(OpCodes.Ldarg_0), new CodeInstruction(OpCodes.Ldstr, "Name"), new CodeInstruction(OpCodes.Ldarg_1),
            new CodeInstruction(OpCodes.Callvirt, original), new CodeInstruction(OpCodes.Ret)
        };
        var patched = SaveNameSerializationPatch.Transpile(source).ToList();
        if (patched.Count != source.Count || patched[3].opcode != OpCodes.Call || ((MethodInfo)patched[3].operand).DeclaringType != typeof(SaveNameEncoding))
            throw new Exception("Unexpected writer-call replacement");
        var method = new DynamicMethod("nameWriter", typeof(void), new[] { typeof(XmlWriter), typeof(string) }, typeof(SaveNameTranspilerProbe).Module, true);
        ILGenerator il = method.GetILGenerator();
        foreach (CodeInstruction instruction in patched)
        {
            if (instruction.operand == null) il.Emit(instruction.opcode);
            else if (instruction.operand is string) il.Emit(instruction.opcode, (string)instruction.operand);
            else il.Emit(instruction.opcode, (MethodInfo)instruction.operand);
        }
        var write = (Action<XmlWriter, string>)method.CreateDelegate(typeof(Action<XmlWriter, string>));
        using (var stream = new MemoryStream())
        using (var writer = new XmlTextWriter(stream, new ASCIIEncoding()))
        {
            write(writer, "파랑🚗<&"); writer.Flush();
            var doc = new XmlDocument(); doc.LoadXml(Encoding.ASCII.GetString(stream.ToArray()));
            if (doc.DocumentElement.InnerText != "파랑🚗<&") throw new Exception("Patched IL lost name data");
        }
        bool rejected = false;
        try { SaveNameSerializationPatch.Transpile(new[] { new CodeInstruction(OpCodes.Ret) }); }
        catch (InvalidOperationException) { rejected = true; }
        if (!rejected) throw new Exception("Missing original writer was accepted");
        Console.WriteLine("PASS save-name writer transpiler: generated IL stack valid; Unicode/XML name preserved; missing writer rejected.");
    }
}

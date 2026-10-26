using System;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using HarmonyLib;
using System.Collections.Generic;


public static class MonoShutdownProbe
{
    [MethodImpl(MethodImplOptions.NoInlining)]
    public static int Target() { return 5; }
    public static void Postfix(ref int __result) { __result += 2; }
    public static void RunPatch()
    {
        Harmony harmony = new Harmony("roadtrip.isolated.shutdown.probe");
        harmony.Patch(
            typeof(MonoShutdownProbe).GetMethod("Target"),
            postfix: new HarmonyMethod(typeof(MonoShutdownProbe).GetMethod("Postfix")));
        Console.WriteLine("PATCH_RESULT=" + Target());
        if (Environment.GetEnvironmentVariable("ROADTRIP_SHUTDOWN_PROBE").Contains("unpatch"))
        {
            harmony.UnpatchSelf();
            Console.WriteLine("UNPATCH_RESULT=" + Target());
        }
    }
    public static int Main()
    {
        Console.WriteLine("PROBE_START");
        if (Environment.GetEnvironmentVariable("ROADTRIP_SHUTDOWN_PROBE") == "corlib")
        {
            Assembly assembly = typeof(MonoShutdownProbe).Assembly;
            IntPtr pointer = (IntPtr)assembly.GetType().GetField("_mono_assembly", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(assembly);
            Console.WriteLine("POINTER_4C_BEFORE=" + Marshal.ReadInt32(pointer, 0x4c).ToString("X8"));
            MonoMod.Utils.Extensions.SetMonoCorlibInternal(assembly, true);
            Console.WriteLine("POINTER_4C_AFTER=" + Marshal.ReadInt32(pointer, 0x4c).ToString("X8"));
            Console.WriteLine("CORLIB_53=" + Marshal.ReadByte(pointer, 0x53));
        }
        if ((Environment.GetEnvironmentVariable("ROADTRIP_SHUTDOWN_PROBE") ?? "").StartsWith("harmony")) RunPatch();
        Console.WriteLine("MANAGED_MAIN_COMPLETE");
        return 0;
    }

}

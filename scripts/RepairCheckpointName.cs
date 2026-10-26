// Explicit, backed-up repair for one known damaged player name. Never runs the game.
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml;

internal static class RepairCheckpointName
{
    private static string Hash(byte[] bytes)
    {
        using (SHA256 algorithm = SHA256.Create()) return BitConverter.ToString(algorithm.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
    }

    private static void Closed()
    {
        if (Process.GetProcessesByName("MonsterCon").Length != 0) throw new Exception("Exit Monster Con before repairing a checkpoint");
    }

    public static void Main(string[] args)
    {
        if (args.Length != 4) throw new ArgumentException("game-directory checkpoint-file original-name new-backup-directory");
        Closed();
        string gamePath = Path.GetFullPath(args[0]);
        string checkpoint = Path.GetFullPath(args[1]);
        string userData = Path.Combine(gamePath, "UserData") + Path.DirectorySeparatorChar;
        if (!checkpoint.StartsWith(userData, StringComparison.OrdinalIgnoreCase) || !checkpoint.EndsWith("_Checkpoint.xml", StringComparison.OrdinalIgnoreCase))
            throw new Exception("Repair target must be the named game's UserData checkpoint");
        string name = args[2];
        if (string.IsNullOrWhiteSpace(name) || name.Trim('?').Length == 0) throw new Exception("A known original name is required");
        string backupDirectory = Path.GetFullPath(args[3]);
        if (Directory.Exists(backupDirectory)) throw new Exception("Use a new backup directory");
        string managed = Path.Combine(gamePath, "MonsterCon_Data", "Managed");
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
            string path = Path.Combine(managed, new AssemblyName(e.Name).Name + ".dll");
            return File.Exists(path) ? Assembly.LoadFrom(path) : null;
        };
        Type crypto = Assembly.LoadFrom(Path.Combine(managed, "Assembly-CSharp.dll")).GetType("BeautifulGlitch.CryptoUtils", true);
        const BindingFlags flags = BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;
        MethodInfo decrypt = crypto.GetMethod("Decrypt", flags);
        MethodInfo encrypt = crypto.GetMethod("Encrypt", flags);
        byte[] original = File.ReadAllBytes(checkpoint);
        var outer = new XmlDocument();
        using (var input = new MemoryStream(original)) outer.Load(input);
        if (outer.DocumentElement.Name != "Checkpoint" || outer.DocumentElement.ChildNodes.Count != 1) throw new Exception("Unexpected encrypted checkpoint structure");
        string cipher = outer.DocumentElement.InnerText;
        string plain = (string)decrypt.Invoke(null, new object[] { cipher });
        var before = new XmlDocument();
        before.LoadXml("<Checkpoint>" + plain + "</Checkpoint>");
        XmlNodeList names = before.SelectNodes("//CorePlayerData/Name");
        if (names.Count != 1 || names[0].InnerText.Length == 0 || names[0].InnerText.Trim('?').Length != 0)
            throw new Exception("Expected exactly one player whose stored name consists only of question marks");
        string replacement;
        using (var stream = new MemoryStream())
        using (var writer = new XmlTextWriter(stream, new ASCIIEncoding()))
        {
            MonsterConKoreanBridge.SaveNameEncoding.WriteElementString(writer, "Name", name);
            writer.Flush(); replacement = Encoding.ASCII.GetString(stream.ToArray());
        }
        var pattern = new Regex("<Name>\\?+</Name>");
        if (pattern.Matches(plain).Count != 1) throw new Exception("Unexpected name element encoding");
        string updatedPlain = pattern.Replace(plain, delegate(Match match) { return replacement; });
        var after = new XmlDocument();
        after.LoadXml("<Checkpoint>" + updatedPlain + "</Checkpoint>");
        if (after.SelectSingleNode("//CorePlayerData/Name").InnerText != name) throw new Exception("Replacement name did not round trip");
        names[0].InnerText = "";
        after.SelectSingleNode("//CorePlayerData/Name").InnerText = "";
        if (before.OuterXml != after.OuterXml) throw new Exception("Non-name progress data changed");
        string updatedCipher = (string)encrypt.Invoke(null, new object[] { updatedPlain });
        if ((string)decrypt.Invoke(null, new object[] { updatedCipher }) != updatedPlain) throw new Exception("Re-encryption integrity mismatch");
        string outerText = Encoding.UTF8.GetString(original);
        int position = outerText.IndexOf(cipher, StringComparison.Ordinal);
        if (position < 0 || outerText.IndexOf(cipher, position + cipher.Length, StringComparison.Ordinal) >= 0) throw new Exception("Unexpected encrypted body location");
        byte[] updated = Encoding.UTF8.GetBytes(outerText.Substring(0, position) + updatedCipher + outerText.Substring(position + cipher.Length));
        Directory.CreateDirectory(backupDirectory);
        string backup = Path.Combine(backupDirectory, Path.GetFileName(checkpoint));
        File.WriteAllBytes(backup, original);
        if (Hash(File.ReadAllBytes(backup)) != Hash(original)) throw new Exception("Backup integrity mismatch");
        string temp = checkpoint + ".codex-name-repair.tmp";
        if (File.Exists(temp)) throw new Exception("Repair staging file already exists");
        using (var stream = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        { stream.Write(updated, 0, updated.Length); stream.Flush(true); }
        Closed();
        if (Hash(File.ReadAllBytes(checkpoint)) != Hash(original)) throw new Exception("Checkpoint changed during repair; original was not replaced");
        File.Replace(temp, checkpoint, null);
        if (Hash(File.ReadAllBytes(checkpoint)) != Hash(updated)) throw new Exception("Repaired checkpoint write integrity mismatch; original backup retained");
        File.WriteAllText(Path.Combine(backupDirectory, "REPAIR_HASHES.txt"),
            "before=" + Hash(original) + "\nafter=" + Hash(updated) + "\nchanged=one Name element only; other decrypted XML unchanged\n", Encoding.ASCII);
        Console.WriteLine("REPAIRED one player name; all other decrypted checkpoint XML unchanged.");
        Console.WriteLine("BACKUP=" + backupDirectory);
    }
}

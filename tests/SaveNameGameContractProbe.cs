using System;
using System.IO;
using System.Reflection;
using System.Runtime.Serialization;
using System.Text;
using System.Xml;
using MonsterConKoreanBridge;

// Pure managed XML/crypto calls only: no scene, game launch or save writes.
internal static class SaveNameGameContractProbe
{
    public static void Main(string[] args)
    {
        try { Run(args); }
        catch (Exception error)
        {
            Console.WriteLine("PROBE ERROR TYPE: " + error.GetType().FullName);
            if (error.InnerException != null) Console.WriteLine("INNER ERROR TYPE: " + error.InnerException.GetType().FullName);
            Environment.ExitCode = 1;
        }
    }

    private static void Run(string[] args)
    {
        string managed = Path.Combine(args[0], "MonsterCon_Data", "Managed");
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
            string path = Path.Combine(managed, new AssemblyName(e.Name).Name + ".dll");
            return File.Exists(path) ? Assembly.LoadFrom(path) : null;
        };
        Assembly game = Assembly.LoadFrom(Path.Combine(managed, "Assembly-CSharp.dll"));
        const BindingFlags all = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static | BindingFlags.Instance;
        Type crypto = game.GetType("BeautifulGlitch.CryptoUtils", true);
        MethodInfo encrypt = crypto.GetMethod("Encrypt", all);
        MethodInfo decrypt = crypto.GetMethod("Decrypt", all);
        MethodInfo read = game.GetType("BeautifulGlitch.CoreXmlSerializer", true).GetMethod("UnserializeString", all, null,
            new[] { typeof(XmlNode), typeof(string), typeof(string) }, null);
        if (read == null) throw new Exception("Original XML string reader not found");
        object readTarget = read.IsStatic ? null : FormatterServices.GetUninitializedObject(game.GetType("BeautifulGlitch.CoreCheckpointXmlSerializer", true));
        foreach (string name in new[] { "파랑", "한글 이름", "이름<&\"'", "여행자🚗" })
        {
            using (var stream = new MemoryStream())
            using (var writer = new XmlTextWriter(stream, new ASCIIEncoding()))
            {
                writer.WriteStartElement("CorePlayerData");
                SaveNameEncoding.WriteElementString(writer, "Name", name);
                SaveNameEncoding.WriteElementString(writer, "Player", "PlayerA");
                writer.WriteEndElement(); writer.Flush();
                var document = new XmlDocument();
                document.LoadXml(Encoding.ASCII.GetString(stream.ToArray()));
                string encrypted = (string)encrypt.Invoke(null, new object[] { document.DocumentElement.InnerXml });
                string decrypted = (string)decrypt.Invoke(null, new object[] { encrypted });
                var restored = new XmlDocument();
                restored.LoadXml("<CorePlayerData>" + decrypted + "</CorePlayerData>");
                if ((string)read.Invoke(readTarget, new object[] { restored.DocumentElement, "Name", "MISSING" }) != name)
                    throw new Exception("Original game crypto/XML reader did not preserve Unicode name");
            }
        }
        Console.WriteLine("PASS original game Encrypt/Decrypt + UnserializeString: four Unicode/XML name round trips; no game execution/save writes.");
        if (args.Length > 1)
        {
            var live = new XmlDocument();
            live.Load(args[1]);
            string plain = (string)decrypt.Invoke(null, new object[] { live.DocumentElement.InnerText });
            var inspected = new XmlDocument();
            inspected.LoadXml("<Checkpoint>" + plain + "</Checkpoint>");
            XmlNodeList names = inspected.SelectNodes("//CorePlayerData/Name");
            int damaged = 0, unicode = 0;
            foreach (XmlNode node in names)
            {
                string value = node.InnerText;
                if (value.Length > 0 && value.Trim('?').Length == 0) damaged++;
                foreach (char c in value) { if (c > 127) { unicode++; break; } }
            }
            Console.WriteLine("READ-ONLY checkpoint: player_names=" + names.Count + " all_question_mark_names=" + damaged + " non_ASCII_names=" + unicode + "; names not printed, checkpoint unchanged.");
        }
    }
}

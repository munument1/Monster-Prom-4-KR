using System;
using System.IO;
using System.Text;
using System.Xml;
using MonsterConKoreanBridge;

internal static class SaveNameEncodingProbe
{
    private static string RoundTrip(string name, bool patched)
    {
        using (MemoryStream stream = new MemoryStream())
        {
            using (XmlTextWriter writer = new XmlTextWriter(stream, new ASCIIEncoding()))
            {
                writer.WriteStartElement("CorePlayerData");
                if (patched) SaveNameEncoding.WriteElementString(writer, "Name", name);
                else writer.WriteElementString("Name", name);
                SaveNameEncoding.WriteElementString(writer, "Player", "PlayerA");
                writer.WriteEndElement();
                writer.Flush();
                byte[] bytes = stream.ToArray();
                foreach (byte value in bytes)
                    if (value > 127) throw new Exception("Save is no longer ASCII-compatible");
                XmlDocument doc = new XmlDocument();
                using (MemoryStream input = new MemoryStream(bytes))
                using (StreamReader reader = new StreamReader(input, Encoding.ASCII)) doc.Load(reader);
                if (doc.SelectSingleNode("/CorePlayerData/Player").InnerText != "PlayerA")
                    throw new Exception("Non-name field changed");
                // EncryptXml consumes the decoded document's InnerXml. Verify
                // another UTF-8 XML serialization preserves that Unicode too.
                XmlDocument reloaded = new XmlDocument();
                reloaded.LoadXml(Encoding.UTF8.GetString(Encoding.UTF8.GetBytes(doc.OuterXml)));
                return reloaded.SelectSingleNode("/CorePlayerData/Name").InnerText;
            }
        }
    }

    public static void Main()
    {
        if (RoundTrip("재클린", false) != "???") throw new Exception("Original data-loss reproduction failed");
        foreach (string name in new[] { "재클린", "한글 이름", "Jacqueline", "이름<&\"'", "여행자🚗", "", "조이 Zoe 123", "日本語", "é" })
            if (RoundTrip(name, true) != name) throw new Exception("Name round-trip failed");
        Console.WriteLine("PASS: original ASCII name loss reproduced; 9 Unicode/XML name round-trips preserved");
    }
}

using System;
using System.Xml;

namespace MonsterConKoreanBridge
{
    // The game's XmlTextWriter uses ASCII with replacement fallback. Emit XML
    // character references for names so its existing ASCII reader and encrypted
    // save format can round-trip Unicode without changing the file encoding.
    public static class SaveNameEncoding
    {
        public static void WriteElementString(XmlWriter writer, string key, string value)
        {
            if (key != "Name" || string.IsNullOrEmpty(value))
            {
                writer.WriteElementString(key, value);
                return;
            }

            writer.WriteStartElement(key);
            for (int i = 0; i < value.Length; i++)
            {
                char character = value[i];
                if (char.IsHighSurrogate(character) && i + 1 < value.Length && char.IsLowSurrogate(value[i + 1]))
                {
                    writer.WriteSurrogateCharEntity(value[++i], character);
                }
                else if (character > 127 && !char.IsSurrogate(character))
                {
                    writer.WriteCharEntity(character);
                }
                else
                {
                    writer.WriteString(character.ToString());
                }
            }
            writer.WriteEndElement();
        }
    }
}

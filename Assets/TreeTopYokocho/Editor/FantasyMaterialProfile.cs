#if UNITY_EDITOR && !COMPILER_UDONSHARP
using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using UnityEngine;

namespace TreeTopYokocho.Editor
{
    [Serializable] public sealed class FantasyFloat { public string name; public float value; }
    [Serializable] public sealed class FantasyVector { public string name; public float[] value; }
    [Serializable] public class FantasySettings
    {
        public string[] keywords;
        public FantasyFloat[] floats;
        public FantasyVector[] vectors;
    }
    [Serializable] public sealed class FantasyMaterialGroup : FantasySettings
    {
        public string[] names;
        public string shader;
        public bool textureKeywords;
    }
    // Editor-only routing. This creates no runtime scripts, lights or effects objects.
    [Serializable] public sealed class FantasyMaterialProfile
    {
        public int schema;
        public string name;
        public FantasyMaterialGroup[] materialGroups;
        public FantasySettings sky;
        [NonSerialized] Dictionary<string, FantasyMaterialGroup> lookup;
        static bool Finite(float v) { return !float.IsNaN(v) && !float.IsInfinity(v); }
        static void ValidateSettings(FantasySettings settings)
        {
            if (settings == null) throw new InvalidDataException("Missing fantasy settings.");
            var names = new HashSet<string>();
            foreach (var entry in settings.floats ?? new FantasyFloat[0]) {
                if (entry == null || string.IsNullOrEmpty(entry.name) || !names.Add(entry.name) || !Finite(entry.value))
                    throw new InvalidDataException("Invalid/duplicate fantasy float.");
            }
            foreach (var entry in settings.vectors ?? new FantasyVector[0]) {
                if (entry == null || string.IsNullOrEmpty(entry.name) || !names.Add(entry.name) || entry.value == null || entry.value.Length != 4)
                    throw new InvalidDataException("Invalid/duplicate fantasy vector.");
                foreach (float value in entry.value) if (!Finite(value)) throw new InvalidDataException("Non-finite fantasy vector.");
            }
            names.Clear();
            foreach (string keyword in settings.keywords ?? new string[0])
                if (string.IsNullOrEmpty(keyword) || !names.Add(keyword) ||
                    (keyword != "_YOKOCHO_CRAFT" && keyword != "_YOKOCHO_FANTASY_SKY"))
                    throw new InvalidDataException("Unknown/duplicate fantasy keyword.");
        }
        // Property/schema preflight only. Shader.Find does not certify compilation.
        static void PreflightShader(string shaderName, FantasySettings settings)
        {
            var shader = Shader.Find(shaderName);
            if (shader == null) throw new InvalidDataException("Missing fantasy shader: " + shaderName);
            Material temporary = null;
            try {
                temporary = new Material(shader);
                foreach (var entry in settings.floats ?? new FantasyFloat[0])
                    if (!temporary.HasProperty(entry.name)) throw new InvalidDataException("Shader lacks fantasy property: " + entry.name);
                foreach (var entry in settings.vectors ?? new FantasyVector[0])
                    if (!temporary.HasProperty(entry.name)) throw new InvalidDataException("Shader lacks fantasy vector: " + entry.name);
            }
            finally { if (temporary != null) UnityEngine.Object.DestroyImmediate(temporary); }
        }
        public static FantasyMaterialProfile Load(string root, MaterialSpec[] materials)
        {
            string path = root + "/Data/FantasyMaterials.json";
            var profile = JsonUtility.FromJson<FantasyMaterialProfile>(File.ReadAllText(path, Encoding.UTF8));
            if (profile == null || profile.schema != 1 || profile.materialGroups == null || profile.materialGroups.Length == 0)
                throw new InvalidDataException("Missing/unsupported fantasy material profile.");
            var known = new HashSet<string>();
            foreach (var material in materials) known.Add(material.name);
            profile.lookup = new Dictionary<string, FantasyMaterialGroup>();
            foreach (var group in profile.materialGroups) {
                if (group == null || group.names == null || group.names.Length == 0 ||
                    (group.shader != "Surface" && group.shader != "Cloth" && group.shader != "LanternPaper" && group.shader != "Water" && group.shader != "Glaze"))
                    throw new InvalidDataException("Invalid fantasy material group.");
                ValidateSettings(group);
                PreflightShader("TreeTopYokocho/" + group.shader, group);
                foreach (string material in group.names) {
                    if (string.IsNullOrEmpty(material) || !known.Contains(material) || profile.lookup.ContainsKey(material))
                        throw new InvalidDataException("Unknown/duplicate fantasy material: " + material);
                    profile.lookup.Add(material, group);
                }
            }
            ValidateSettings(profile.sky);
            PreflightShader("TreeTopYokocho/BlueHourSky", profile.sky);
            return profile;
        }
        public FantasyMaterialGroup Find(string material)
        {
            FantasyMaterialGroup group;
            return lookup.TryGetValue(material, out group) ? group : null;
        }
        public static void Apply(Material material, FantasySettings settings)
        {
            if (settings == null) return;
            foreach (var entry in settings.floats ?? new FantasyFloat[0]) {
                if (!material.HasProperty(entry.name)) throw new InvalidDataException("Shader lacks fantasy property: " + entry.name);
                material.SetFloat(entry.name, entry.value);
            }
            foreach (var entry in settings.vectors ?? new FantasyVector[0]) {
                if (!material.HasProperty(entry.name)) throw new InvalidDataException("Shader lacks fantasy vector: " + entry.name);
                material.SetVector(entry.name, new Vector4(entry.value[0], entry.value[1], entry.value[2], entry.value[3]));
            }
            foreach (string keyword in settings.keywords ?? new string[0]) material.EnableKeyword(keyword);
        }
    }
}
#endif

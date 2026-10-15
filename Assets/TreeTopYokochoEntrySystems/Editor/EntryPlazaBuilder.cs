#if UNITY_EDITOR && !COMPILER_UDONSHARP
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UdonSharp;
using UdonSharpEditor;

namespace TreeTopYokocho.EntrySystems.Editor
{
    [Serializable] public sealed class EntryMaterialSpec { public string name, texture; public float[] color; public float roughness; }
    [Serializable] public sealed class EntryBoxSpec { public string name; public float[] center, size, axes; }
    [Serializable] public sealed class EntryWarpSpec { public string id, label; public float[] position, size, destination, forward, approach; public float range; }
    [Serializable] public sealed class EntryAnchorSpec { public float[] position, forward, usableMin, usableMax, standing, buttonSize, reservedVolumeMin, reservedVolumeMax; public float frontY; }
    [Serializable] public sealed class EntryPreservationSpec { public int stations; public string coreManifestSha256; }
    [Serializable] public sealed class EntryPlazaSpec
    {
        public int schemaVersion, addedLights, addedStations, triangles, meshCount;
        public string ownerRoot, childRoot, coreRoot, baselineVersion, nativeGeometry;
        public EntryMaterialSpec[] materials;
        public EntryBoxSpec[] solidBoxes;
        public EntryWarpSpec[] warps;
        public EntryAnchorSpec systemsControlAnchor;
        public EntryPreservationSpec preservation;
    }
    public static class EntryPlazaBuilder
    {
        public const string Version = "entry-plaza-1";
        public const string AssetRoot = "Assets/TreeTopYokochoEntrySystems/EntryPlaza";
        public const string ConfigPath = AssetRoot + "/Data/EntryPlaza.json";
        // Reviewed literal pins. Regeneration MUST NOT update these automatically.
        public const string ApprovedConfigSha256 = "599cd99a77fd810e983dc2303197d0bb381c7019816f3ca21eebee7d37555afe";
        public const string ApprovedNativeSha256 = "15cdf7f69dff7e3977d3ef601697de881f0e429331bcc54b4717e34fc516465f";
        static readonly Dictionary<string, string> ApprovedFiles = new Dictionary<string, string>
        {
            { "Data/EntryPlaza.json", "599cd99a77fd810e983dc2303197d0bb381c7019816f3ca21eebee7d37555afe" },
            { "Data/EntryPlazaMeshes.bytes", "15cdf7f69dff7e3977d3ef601697de881f0e429331bcc54b4717e34fc516465f" },
            { "Textures/EntryControls.png", "0c6986fd7b4ee185a4f564c48d0e88426ad330f718863b6ff568e82f491f5905" },
            { "Textures/EntryControlsHeader.png", "7c9b2dd4d4f25076e8b9a1c2a621dc0cd6b65592bdbee054d39b98ffe7264135" },
            { "Textures/EntryEndgrain.png", "217b158360e76c43e9190804b4b89409ab7cd3c6b13cbce064ee28befa3f861f" },
            { "Textures/EntryGuideboard.png", "5c8a17bb8634443d19306b7c89b1f328a95f5c3043ab99808aedd7189121a44b" },
            { "Textures/EntryTimber.png", "1f086935451397d15f6c32349eba2478b5afd882c21d10a635b4b8c7338035b3" },
            { "Textures/EntryWarp0.png", "3564061306df8f76c69bb57e0bdc43b30ff2d4afa1fffa4ad33c066c36ebd98a" },
            { "Textures/EntryWarp1.png", "8c3d864ec947a83462896e1ae257200f3ceb65bd3a2410b51e0153cc0c779e6b" },
            { "Textures/EntryWarp2.png", "f3a14e55bc86ee0d1109525a7865ec5c82b99792ca894b4ba07516ff950ed35c" },
        };
        public static string ConfigDigest { get { return Digest(File.ReadAllBytes(ConfigPath)); } }
        public static Vector3 SourceToUnity(float[] p) { return new Vector3(p[0], p[2], p[1]); }
        static bool Finite(float v) { return !float.IsNaN(v) && !float.IsInfinity(v); }
        static void Vector(float[] v, string label, bool positive = false)
        {
            if (v == null || v.Length != 3 || v.Any(x => !Finite(x) || (positive && x <= 0)))
                throw new InvalidDataException("Invalid entry vector: " + label);
        }
        static string Digest(byte[] bytes)
        {
            using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
        }
        static string SafeFile(string value)
        {
            if (string.IsNullOrEmpty(value) || value != Path.GetFileName(value) || value.Contains("..")) throw new InvalidDataException("Invalid entry asset filename.");
            return value;
        }
        public static EntryPlazaSpec LoadConfig()
        {
            return JsonUtility.FromJson<EntryPlazaSpec>(File.ReadAllText(ConfigPath, Encoding.UTF8));
        }
        /// <summary>Validate all source input without mutating assets or the open scene.</summary>
        public static void Preflight()
        {
            foreach (var entry in ApprovedFiles)
            {
                string path = AssetRoot + "/" + entry.Key;
                if (!File.Exists(path) || Digest(File.ReadAllBytes(path)) != entry.Value)
                    throw new InvalidDataException("Entrance asset differs from the reviewed geometry/art checkpoint: " + entry.Key);
            }
            if (ConfigDigest != ApprovedConfigSha256 || Digest(File.ReadAllBytes(AssetRoot + "/Data/EntryPlazaMeshes.bytes")) != ApprovedNativeSha256)
                throw new InvalidDataException("Entrance checkpoint constants are inconsistent.");
            var spec = LoadConfig();
            if (spec == null || spec.schemaVersion != 1 || spec.ownerRoot != "EntrySystems_v1" || spec.childRoot != "EntryPlaza" || spec.coreRoot != "TreeTopYokocho_v2" || spec.baselineVersion != "2.19.0")
                throw new InvalidDataException("Unexpected entrance ownership/baseline contract.");
            if (spec.addedLights != 0 || spec.addedStations != 0 || spec.preservation == null || spec.preservation.stations != 49)
                throw new InvalidDataException("The entrance addon must preserve lights and the 49 existing stations.");
            if (spec.materials == null || spec.solidBoxes == null || spec.warps == null || spec.warps.Length != 3 || spec.systemsControlAnchor == null)
                throw new InvalidDataException("Incomplete entrance config.");
            string corePath = "Assets/TreeTopYokocho/Data/WorldManifest.json";
            if (Digest(File.ReadAllBytes(corePath)) != spec.preservation.coreManifestSha256)
                throw new InvalidDataException("Core manifest differs from the immutable, audited v2.19 checkpoint. Re-audit this addon before installation.");
            var names = new HashSet<string>();
            foreach (var material in spec.materials)
            {
                if (string.IsNullOrEmpty(material.name) || !names.Add(material.name)) throw new InvalidDataException("Duplicate or empty entrance material.");
                Vector(material.color, material.name);
                if (!Finite(material.roughness) || material.roughness < 0 || material.roughness > 1) throw new InvalidDataException("Invalid material roughness.");
                if (!string.IsNullOrEmpty(material.texture))
                {
                    string path = AssetRoot + "/Textures/" + SafeFile(material.texture);
                    if (!File.Exists(path) || AssetDatabase.LoadAssetAtPath<Texture2D>(path) == null) throw new InvalidDataException("Missing/import-failed entrance texture: " + path);
                }
            }
            foreach (var b in spec.solidBoxes)
            {
                Vector(b.center, b.name); Vector(b.size, b.name, true);
                if (b.axes == null || b.axes.Length != 9 || b.axes.Where((v, i) => !Finite(v) || Math.Abs(v - (i % 4 == 0 ? 1 : 0)) > .00001f).Any())
                    throw new InvalidDataException("Entrance boxes must use the audited identity source axes.");
            }
            var expectedLevels = new HashSet<string> { "Entry_To_G0", "Entry_To_L2", "Entry_To_L3" };
            foreach (var w in spec.warps)
            {
                if (!expectedLevels.Remove(w.id)) throw new InvalidDataException("Unexpected or duplicate entrance warp.");
                Vector(w.position, w.id); Vector(w.size, w.id, true); Vector(w.destination, w.id); Vector(w.forward, w.id); Vector(w.approach, w.id);
                float expectedZ = w.id == "Entry_To_G0" ? .08f : (w.id == "Entry_To_L2" ? 140.08f : 146.08f);
                if (Math.Abs(w.destination[2] - expectedZ) > .001f || !Finite(w.range) || Math.Abs(w.destination[0] + 16) > .001f || Math.Abs(w.destination[1] + 18.55f) > .001f || SourceToUnity(w.forward).sqrMagnitude < .99f || w.range < .5f || w.range > 2.2f)
                    throw new InvalidDataException("Warp is outside the reviewed landing/interaction contract.");
            }
            Vector(spec.systemsControlAnchor.position, "Controls anchor"); Vector(spec.systemsControlAnchor.forward, "Controls forward"); Vector(spec.systemsControlAnchor.standing, "Controls standing");
            var geometry = ReadGeometry(AssetRoot + "/Data/" + SafeFile(spec.nativeGeometry), names);
            if (geometry.Count != spec.meshCount || geometry.Sum(x => x.faces.Length / 3) != spec.triangles) throw new InvalidDataException("Entrance geometry count differs from reviewed manifest.");
            if (Shader.Find("Standard") == null) throw new InvalidOperationException("Built-in Standard shader is required for entrance materials.");
        }
        sealed class NativeMesh
        {
            public string group, material;
            public Vector3[] vertices;
            public Vector2[] uv;
            public Color32[] colors;
            public int[] faces;
        }
        static string ReadName(BinaryReader r)
        {
            int n = r.ReadInt32(); if (n < 1 || n > 4096) throw new InvalidDataException("Invalid entrance mesh name.");
            var bytes = r.ReadBytes(n); if (bytes.Length != n) throw new EndOfStreamException(); return Encoding.UTF8.GetString(bytes);
        }
        static List<NativeMesh> ReadGeometry(string path, HashSet<string> materialNames)
        {
            var result = new List<NativeMesh>();
            using (var r = new BinaryReader(File.OpenRead(path), Encoding.UTF8))
            {
                if (Encoding.ASCII.GetString(r.ReadBytes(4)) != "JYWM" || r.ReadInt32() != 1) throw new InvalidDataException("Invalid entrance geometry header.");
                int count = r.ReadInt32(); if (count < 1 || count > 128) throw new InvalidDataException("Invalid entrance mesh count.");
                for (int i = 0; i < count; i++)
                {
                    var n = new NativeMesh { group = ReadName(r), material = ReadName(r) };
                    if (!n.group.StartsWith("EntryPlaza/", StringComparison.Ordinal) || !materialNames.Contains(n.material)) throw new InvalidDataException("Unowned entrance mesh or material.");
                    int vc = r.ReadInt32(), ic = r.ReadInt32();
                    if (vc < 3 || vc > 100000 || ic < 3 || ic > 300000 || ic % 3 != 0) throw new InvalidDataException("Invalid entrance geometry dimensions.");
                    n.vertices = new Vector3[vc]; n.uv = new Vector2[vc]; n.colors = new Color32[vc]; n.faces = new int[ic];
                    for (int j = 0; j < vc; j++)
                    {
                        float x = r.ReadSingle(), y = r.ReadSingle(), z = r.ReadSingle();
                        if (!Finite(x) || !Finite(y) || !Finite(z)) throw new InvalidDataException("Nonfinite entrance vertex.");
                        n.vertices[j] = new Vector3(x, z, y);
                    }
                    for (int j = 0; j < vc; j++) { float u = r.ReadSingle(), v = r.ReadSingle(); if (!Finite(u) || !Finite(v)) throw new InvalidDataException("Invalid entrance UV."); n.uv[j] = new Vector2(u, v); }
                    for (int j = 0; j < vc; j++) n.colors[j] = new Color32(r.ReadByte(), r.ReadByte(), r.ReadByte(), r.ReadByte());
                    for (int j = 0; j < ic; j += 3)
                    {
                        int a = r.ReadInt32(), b = r.ReadInt32(), c = r.ReadInt32();
                        if (a < 0 || b < 0 || c < 0 || a >= vc || b >= vc || c >= vc) throw new InvalidDataException("Entrance index out of bounds.");
                        n.faces[j] = a; n.faces[j + 1] = c; n.faces[j + 2] = b;
                    }
                    result.Add(n);
                }
                if (r.BaseStream.Position != r.BaseStream.Length) throw new InvalidDataException("Trailing entrance geometry data.");
            }
            return result;
        }
        static void SetInteractionMember(object target, string name, object value)
        {
            const BindingFlags flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;
            var field = target.GetType().GetField(name, flags);
            if (field != null) { field.SetValue(target, value); return; }
            var property = target.GetType().GetProperty(name, flags);
            if (property != null && property.CanWrite) { property.SetValue(target, value); return; }
            throw new MissingMemberException(target.GetType().FullName, name);
        }
        /// <summary>Caller owns the scene-sibling root and all install/undo/save/publication decisions.</summary>
        public static void Build(Transform root, string generatedAssetDirectory)
        {
            Preflight();
            if (root == null || root.name != "EntrySystems_v1" || root.parent != null || !root.gameObject.scene.IsValid() || root.localScale != Vector3.one || root.position != Vector3.zero || root.rotation != Quaternion.identity)
                throw new InvalidOperationException("Installer must supply the identity scene-sibling EntrySystems_v1 root.");
            if (root.Find("EntryPlaza") != null) throw new InvalidOperationException("EntryPlaza already exists. Use the owning installer's controlled replace flow.");
            var core = root.gameObject.scene.GetRootGameObjects().SingleOrDefault(x => x.name == "TreeTopYokocho_v2");
            if (core == null) throw new InvalidOperationException("Open the built v2.19 world before adding entrance systems.");
            var recovery = core.GetComponentInChildren<YokochoSafety>(true);
            if (recovery == null || recovery.walkableFloors == null || recovery.walkableFloors.Length == 0 || core.GetComponentsInChildren<YokochoSeat>(true).Length != 49)
                throw new InvalidOperationException("Validated core recovery/stations are missing.");
            if (string.IsNullOrEmpty(generatedAssetDirectory) || !generatedAssetDirectory.StartsWith("Assets/TreeTopYokochoEntrySystems/Generated/", StringComparison.Ordinal) || generatedAssetDirectory.Contains("..") || generatedAssetDirectory.Contains("\\") || !AssetDatabase.IsValidFolder(generatedAssetDirectory))
                throw new InvalidOperationException("Installer must supply a fresh owned generated asset directory.");
            var spec = LoadConfig(); string generated = generatedAssetDirectory.TrimEnd('/') + "/EntryPlaza";
            if (Directory.Exists(generated) || AssetDatabase.IsValidFolder(generated)) throw new InvalidOperationException("Entry assets already exist; refusing an in-place overwrite.");
            Directory.CreateDirectory(generated); AssetDatabase.Refresh();
            var materials = new Dictionary<string, Material>();
            foreach (var m in spec.materials)
            {
                string path = generated + "/" + m.name + ".mat";
                var material = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (material == null)
                {
                    material = new Material(Shader.Find("Standard")) { name = m.name, enableInstancing = true };
                    material.color = new Color(m.color[0], m.color[1], m.color[2]);
                    material.SetFloat("_Glossiness", 1 - m.roughness); material.SetFloat("_Metallic", m.name == "EntryPatinatedBrass" ? .65f : 0);
                    if (!string.IsNullOrEmpty(m.texture)) material.mainTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(AssetRoot + "/Textures/" + m.texture);
                    AssetDatabase.CreateAsset(material, path);
                }
                materials.Add(m.name, material);
            }
            var parent = new GameObject("EntryPlaza").transform; parent.SetParent(root, false);
            var visual = new GameObject("StaticTimberAndSigns").transform; visual.SetParent(parent, false);
            var native = ReadGeometry(AssetRoot + "/Data/" + spec.nativeGeometry, new HashSet<string>(materials.Keys));
            // Merge only within this addon, per material. The core's existing batching/culling is untouched.
            foreach (var group in native.GroupBy(n => n.material))
            {
                string path = generated + "/" + group.Key + ".asset";
                var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
                if (mesh == null)
                {
                    var vertices = new List<Vector3>(); var uv = new List<Vector2>(); var colors = new List<Color32>(); var indices = new List<int>();
                    foreach (var item in group) { int offset = vertices.Count; vertices.AddRange(item.vertices); uv.AddRange(item.uv); colors.AddRange(item.colors); indices.AddRange(item.faces.Select(i => i + offset)); }
                    mesh = new Mesh { name = group.Key, indexFormat = vertices.Count > 65535 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                    mesh.SetVertices(vertices); mesh.SetUVs(0, uv); mesh.SetColors(colors); mesh.SetTriangles(indices, 0); mesh.RecalculateNormals(); mesh.RecalculateTangents(); mesh.RecalculateBounds();
                    AssetDatabase.CreateAsset(mesh, path);
                }
                var go = new GameObject(group.Key); go.transform.SetParent(visual, false); go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var renderer = go.AddComponent<MeshRenderer>(); renderer.sharedMaterial = materials[group.Key]; renderer.shadowCastingMode = ShadowCastingMode.On; renderer.receiveShadows = true; renderer.lightProbeUsage = LightProbeUsage.BlendProbes;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
            }
            var solids = new GameObject("FurnitureColliders").transform; solids.SetParent(parent, false);
            foreach (var b in spec.solidBoxes)
            {
                var go = new GameObject(b.name.Replace('/', '_')); go.transform.SetParent(solids, false); go.transform.position = SourceToUnity(b.center);
                var collider = go.AddComponent<BoxCollider>(); collider.size = SourceToUnity(b.size); collider.isTrigger = false;
            }
            var controlsAnchor = new GameObject("SystemsControlAnchor").transform; controlsAnchor.SetParent(parent, false); controlsAnchor.position = SourceToUnity(spec.systemsControlAnchor.position); controlsAnchor.rotation = Quaternion.LookRotation(SourceToUnity(spec.systemsControlAnchor.forward));
            var warps = new GameObject("WayfindingWarps").transform; warps.SetParent(parent, false);
            foreach (var w in spec.warps)
            {
                var go = new GameObject(w.id); go.transform.SetParent(warps, false); go.transform.position = SourceToUnity(w.position); go.layer = 8;
                var collider = go.AddComponent<BoxCollider>(); collider.size = SourceToUnity(w.size); collider.isTrigger = true;
                var target = new GameObject(w.id + "_SafeArrival").transform; target.SetParent(warps, false); target.position = SourceToUnity(w.destination); target.rotation = Quaternion.LookRotation(SourceToUnity(w.forward));
                var teleport = go.AddUdonSharpComponent<YokochoTeleport>(); teleport.destination = target; teleport.recovery = recovery; teleport.ApplyProxyModifications();
                var udon = UdonSharpEditorUtility.GetBackingUdonBehaviour(teleport);
                if (udon == null) throw new InvalidOperationException("Missing entrance Udon backing behaviour.");
                SetInteractionMember(udon, "interactText", w.label); SetInteractionMember(udon, "proximity", w.range); EditorUtility.SetDirty(udon);
            }
            AssetDatabase.SaveAssets();
            // No scene save, scene replacement, light bake, station creation, SDK upload, or core reparenting.
        }
    }
}
#endif

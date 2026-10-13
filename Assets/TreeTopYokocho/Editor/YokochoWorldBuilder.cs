#if UNITY_EDITOR && !COMPILER_UDONSHARP
using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Reflection;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using UdonSharp;
using UdonSharpEditor;

namespace TreeTopYokocho.Editor
{
    [Serializable] public class MaterialSpec { public string name, texture, normal, arm, height, shader; public float[] color; public float emission, roughness, metallic, uvScale = 1, normalScale = 1, parallax, alphaClip = .4f; }
    [Serializable] public class LightSpec { public float[] position; public float range, strength; }
    [Serializable] public class PositionSpec { public float[] position; public string id; }
    [Serializable] public class SeatSpec { public string name, shop; public float[] position, exit, forward; }
    [Serializable] public class TeleportSpec { public string name, label; public float[] position, size, destination, forward; }
    [Serializable] public class BoxSpec { public string name; public float[] center, size, axes; }
    [Serializable] public class WallTest { public float[] start, end; }
    [Serializable] public class AltitudeSpec { public float addedAlleyHeight; }
    [Serializable] public class Manifest
    {
        public string version, title;
        public AltitudeSpec altitudeProfile;
        public MaterialSpec[] materials;
        public LightSpec[] lights;
        public PositionSpec[] spawns, floorTests, steam;
        public SeatSpec[] stations;
        public TeleportSpec[] teleports;
        public BoxSpec[] solidBoxes;
        public WallTest[] wallTests;
        public float respawnHeight;
        public int visualTriangles;
    }

    public static class YokochoWorldBuilder
    {
        const string Root = "Assets/TreeTopYokocho";
        const int FloorLayer = 0;
        const int BarrierLayer = 8; // VRChat Interactive: no stickers on invisible walls.
        const int LocalPlayerLayer = 10;
        static readonly HashSet<string> ImportedTextures = new HashSet<string>();
        public static Vector3 U(float[] p) { return new Vector3(p[0], p[2], p[1]); }
        static Vector3 Axis(float[] a, int i) { return new Vector3(a[i * 3], a[i * 3 + 2], a[i * 3 + 1]); }
        static Manifest ReadManifest()
        {
            var m = JsonUtility.FromJson<Manifest>(File.ReadAllText(Root + "/Data/WorldManifest.json", Encoding.UTF8));
            if (m == null || m.materials == null || m.materials.Length == 0 || m.spawns == null || m.spawns.Length == 0
                || m.floorTests == null || m.wallTests == null || m.stations == null || m.teleports == null || m.solidBoxes == null)
                throw new InvalidDataException("WorldManifest is missing required material, spawn, interaction or safety arrays.");
            if (m.lights == null) m.lights = new LightSpec[0];
            foreach (var material in m.materials)
                if (string.IsNullOrEmpty(material.name) || material.color == null || material.color.Length < 3)
                    throw new InvalidDataException("A manifest material has no name or RGB colour.");
            return m;
        }

        // Source payloads are editor inputs, never loaded by Udon or bundled as Resources.
        // Prefer gzip when both exist so a stale unpacked file cannot win over regeneration.
        static Stream OpenGeometry(string path)
        {
            try
            {
                if (File.Exists(path + ".gz")) return new GZipStream(File.OpenRead(path + ".gz"), CompressionMode.Decompress);
                string directory = Path.GetDirectoryName(path);
                string prefix = Path.GetFileName(path) + ".gz.part";
                string[] parts = Directory.Exists(directory)
                    ? Directory.GetFiles(directory, prefix + "*").Where(x => !x.EndsWith(".meta", StringComparison.OrdinalIgnoreCase)).OrderBy(x => x, StringComparer.Ordinal).ToArray()
                    : new string[0];
                if (parts.Length > 0)
                {
                    if (parts.Length > 128) throw new InvalidDataException("Too many compressed geometry shards.");
                    var combined = new MemoryStream();
                    try
                    {
                        for (int i = 0; i < parts.Length; i++)
                        {
                            string expected = prefix + i.ToString("D3");
                            if (Path.GetFileName(parts[i]) != expected)
                                throw new InvalidDataException("Missing or misnamed geometry shard. Expected " + expected + ".");
                            long size = new FileInfo(parts[i]).Length;
                            if (size < 1 || size > 4L * 1024 * 1024)
                                throw new InvalidDataException("Geometry shard must contain 1 byte to 4 MiB: " + parts[i]);
                            using (var input = File.OpenRead(parts[i])) input.CopyTo(combined);
                        }
                        combined.Position = 0;
                        // Disposing GZipStream also disposes the assembled buffer.
                        return new GZipStream(combined, CompressionMode.Decompress);
                    }
                    catch { combined.Dispose(); throw; }
                }
                if (File.Exists(path)) return File.OpenRead(path);
                throw new FileNotFoundException("Missing geometry source: " + path + "[.gz or .gz.part000...]");
            }
            catch (Exception e) when (e is IOException || e is InvalidDataException)
            {
                throw new InvalidDataException("Cannot open geometry source " + path + ". Verify that every numbered shard is present and unchanged.", e);
            }
        }

        static string ReadName(BinaryReader reader)
        {
            int length = reader.ReadInt32();
            if (length < 1 || length > 4096) throw new InvalidDataException("Invalid mesh name length.");
            byte[] data = reader.ReadBytes(length);
            if (data.Length != length) throw new EndOfStreamException("Truncated mesh name.");
            string name = Encoding.UTF8.GetString(data);
            if (name.Contains("..") || name.Contains("\\") || name.StartsWith("/") || name.EndsWith("/"))
                throw new InvalidDataException("Invalid mesh group/name.");
            return name;
        }

        [MenuItem("Tools/TreeTop Yokocho/1 - Build World")]
        public static void Build()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            Type descriptorType = FindType("VRC.SDK3.Components.VRCSceneDescriptor");
            Type stationType = FindType("VRC.SDK3.Components.VRCStation");
            if (descriptorType == null || stationType == null)
                throw new InvalidOperationException("Create a VCC Worlds project with the current Worlds SDK and UdonSharp first.");
            if (GraphicsSettings.currentRenderPipeline != null)
                throw new InvalidOperationException("This package requires a Built-in Render Pipeline VCC Worlds project.");
            var manifest = ReadManifest();
            ImportedTextures.Clear();
            var shader = Shader.Find("TreeTopYokocho/Surface");
            if (shader == null) throw new InvalidOperationException("The TreeTopYokocho surface shader has not imported.");
            Directory.CreateDirectory(Root + "/Generated");
            AssetDatabase.Refresh();
            string generated = AssetDatabase.GenerateUniqueAssetPath(Root + "/Generated/World");
            Directory.CreateDirectory(generated + "/Meshes");
            Directory.CreateDirectory(generated + "/Materials");
            AssetDatabase.Refresh();

            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var world = new GameObject("TreeTopYokocho_v2");
            var materials = new Dictionary<string, Material>();
            foreach (var m in manifest.materials)
            {
                Shader selectedShader = string.IsNullOrEmpty(m.shader) ? shader : Shader.Find("TreeTopYokocho/" + m.shader);
                if (selectedShader == null) throw new InvalidOperationException("Missing shader for " + m.name);
                var material = new Material(selectedShader) { name = m.name, enableInstancing = true };
                material.SetColor("_Color", new Color(m.color[0], m.color[1], m.color[2], m.color.Length > 3 ? m.color[3] : 1));
                if (material.HasProperty("_Cutoff")) material.SetFloat("_Cutoff", m.alphaClip > 0 ? m.alphaClip : .4f);
                if (selectedShader.name == "TreeTopYokocho/Surface" || selectedShader.name == "TreeTopYokocho/Foliage") {
                    if (!string.IsNullOrEmpty(m.normal)) material.EnableKeyword("_YOKOCHO_NORMALMAP");
                    if (!string.IsNullOrEmpty(m.arm)) material.EnableKeyword("_YOKOCHO_ARM");
                    if (!string.IsNullOrEmpty(m.height) && m.parallax > 0) material.EnableKeyword("_YOKOCHO_PARALLAX");
                }
                if (material.HasProperty("_Emission")) material.SetFloat("_Emission", m.emission);
                if (material.HasProperty("_Roughness")) material.SetFloat("_Roughness", m.roughness);
                if (material.HasProperty("_Metallic")) material.SetFloat("_Metallic", m.metallic);
                if (material.HasProperty("_NormalStrength")) material.SetFloat("_NormalStrength", m.normalScale > 0 ? m.normalScale : 1);
                if (material.HasProperty("_Parallax")) material.SetFloat("_Parallax", m.parallax);
                BindTexture(material, "_MainTex", m.texture, false, true);
                BindTexture(material, "_BumpMap", m.normal, true, false);
                BindTexture(material, "_ARM", m.arm, false, false);
                BindTexture(material, "_HeightMap", m.height, false, false);
                float scale = m.uvScale > 0 ? m.uvScale : 1;
                if (material.HasProperty("_MainTex")) material.mainTextureScale = Vector2.one * scale;
                if (m.name == "Kawara" && material.HasProperty("_Cull")) material.SetFloat("_Cull", 0);
                material.globalIlluminationFlags = m.emission > 0 && m.shader != "Beacon" ? MaterialGlobalIlluminationFlags.BakedEmissive : MaterialGlobalIlluminationFlags.EmissiveIsBlack;
                AssetDatabase.CreateAsset(material, generated + "/Materials/" + m.name + ".mat");
                materials.Add(m.name, material);
            }
            try
            {
                EditorUtility.DisplayProgressBar("Tree-top Yokocho", "Creating the editable world geometry", .2f);
                ReadGeometry(Root + "/Data/VisualMeshes.bytes", world.transform, generated, materials, false);
                EditorUtility.DisplayProgressBar("Tree-top Yokocho", "Creating floor and fall protection colliders", .50f);
                var floorColliders = ReadGeometry(Root + "/Data/CollisionMeshes.bytes", world.transform, generated, materials, true);
                Transform solids = Group(world.transform, "Collision/Solids");
                foreach (var b in manifest.solidBoxes)
                {
                    var go = new GameObject(b.name);
                    go.transform.SetParent(solids, false);
                    go.transform.position = U(b.center);
                    // Source axes are X/Y/Z. A BoxCollider is symmetric, so the
                    // reflected local Y sign does not affect its occupied volume.
                    go.transform.rotation = Quaternion.LookRotation(Axis(b.axes, 1), Axis(b.axes, 2));
                    var collider = go.AddComponent<BoxCollider>();
                    collider.size = U(b.size);
                    go.layer = FloorLayer; go.isStatic = true;
                }

                Transform spawnRoot = Group(world.transform, "WorldSetup/Spawns");
                var spawns = new List<Transform>();
                for (int i = 0; i < manifest.spawns.Length; i++)
                {
                    var s = new GameObject("Spawn_" + (i + 1)).transform;
                    s.SetParent(spawnRoot, false); s.position = U(manifest.spawns[i].position);
                    s.rotation = Quaternion.identity; spawns.Add(s);
                }
                var descriptorGO = new GameObject("VRCWorld");
                descriptorGO.transform.SetParent(world.transform, false);
                descriptorGO.transform.position = spawns[0].position;
                var descriptor = descriptorGO.AddComponent(descriptorType);
                Type pipelineType = FindType("VRC.Core.PipelineManager");
                if (pipelineType != null && descriptorGO.GetComponent(pipelineType) == null) descriptorGO.AddComponent(pipelineType);
                SetMember(descriptor, "spawns", spawns.ToArray(), true);
                SetMember(descriptor, "RespawnHeight", manifest.respawnHeight, true);
                SetMember(descriptor, "spawnOrder", 0, false);
                SetMember(descriptor, "spawnRadius", 0f, false);
                var reference = new GameObject("ReferenceCamera").AddComponent<Camera>();
                reference.transform.SetParent(world.transform, false);
                reference.transform.position = spawns[0].position + Vector3.up * 1.6f;
                reference.nearClipPlane = .03f; reference.farClipPlane = 6000;
                reference.allowHDR = true; reference.enabled = false;
                SetMember(descriptor, "ReferenceCamera", reference, true);

                EditorUtility.DisplayProgressBar("Tree-top Yokocho", "Setting up seating and local floor selection", .72f);
                Transform seats = Group(world.transform, "Interactions/Seats");
                foreach (var s in manifest.stations)
                {
                    var go = new GameObject(s.name);
                    go.transform.SetParent(seats, false); go.transform.position = U(s.position);
                    go.transform.rotation = Quaternion.LookRotation(U(s.forward));
                    go.layer = BarrierLayer;
                    var collider = go.AddComponent<BoxCollider>();
                    collider.size = new Vector3(.48f, .45f, .48f); collider.center = Vector3.up * .12f; collider.isTrigger = true;
                    var station = go.AddComponent(stationType);
                    var entry = new GameObject("Enter").transform;
                    entry.SetParent(go.transform, false);
                    var exit = new GameObject("Exit").transform;
                    exit.SetParent(go.transform, false); exit.position = U(s.exit);
                    SetMember(station, "stationEnterPlayerLocation", entry, true);
                    SetMember(station, "stationExitPlayerLocation", exit, true);
                    SetMember(station, "seated", true, true);
                    SetMember(station, "disableStationExit", false, false);
                    SetMember(station, "canUseStationFromStation", true, false);
                    SetMember(station, "PlayerMobility", "Immobilize", true);
                    var script = go.AddUdonSharpComponent<YokochoSeat>();
                    script.ApplyProxyModifications();
                    ConfigureInteraction(script, "座る", 1.7f);
                }
                Transform lifts = Group(world.transform, "Interactions/Lift");
                foreach (var p in manifest.teleports)
                {
                    var go = new GameObject(p.name);
                    go.transform.SetParent(lifts, false); go.transform.position = U(p.position); go.layer = BarrierLayer;
                    var collider = go.AddComponent<BoxCollider>();
                    collider.size = U(p.size); collider.isTrigger = true;
                    var dest = new GameObject("Destination_" + p.label).transform;
                    dest.SetParent(lifts, false); dest.position = U(p.destination);
                    dest.rotation = Quaternion.LookRotation(U(p.forward));
                    var script = go.AddUdonSharpComponent<YokochoTeleport>();
                    script.destination = dest; script.ApplyProxyModifications();
                    ConfigureInteraction(script, p.label + " へ移動", 2.2f);
                }
                var safetyGO = new GameObject("FallRecovery"); safetyGO.transform.SetParent(world.transform, false);
                var safety = safetyGO.AddUdonSharpComponent<YokochoSafety>();
                safety.arrival = spawns[0]; safety.walkableFloors = floorColliders.ToArray();
                safety.minimumHeight = manifest.respawnHeight + 1f;
                safety.ApplyProxyModifications();
                foreach (var seat in world.GetComponentsInChildren<YokochoSeat>(true)) {
                    seat.recovery = safety; seat.exitPoint = seat.transform.Find("Exit"); seat.ApplyProxyModifications();
                }
                foreach (var lift in world.GetComponentsInChildren<YokochoTeleport>(true)) {
                    lift.recovery = safety; lift.ApplyProxyModifications();
                }
                ConfigureEnvironment(world.transform, generated, manifest);
                try { ConfigurePostProcessing(world.transform, generated, reference); }
                catch (Exception e) { Debug.LogWarning("Optional post processing could not be configured: " + e.Message + ". Core world is preserved; use menu 6 after fixing PPS v2."); }
                AssetDatabase.SaveAssets();
                string scenePath = generated + "/TreeTopYokocho.unity";
                EditorSceneManager.SaveScene(scene, scenePath);
                Selection.activeGameObject = world;
                var view = SceneView.lastActiveSceneView;
                if (view != null) view.LookAt(new Vector3(0, 43 + (manifest.altitudeProfile != null ? manifest.altitudeProfile.addedAlleyHeight : 0), -5), Quaternion.Euler(18, -38, 0), 60);
                Debug.Log("Tree-top Yokocho created: " + scenePath + ". Run the physics audit, then SDK Build & Test. No upload was performed.");
                Audit();
                AuditBudget();
            }
            finally { EditorUtility.ClearProgressBar(); }
        }

        static List<Collider> ReadGeometry(string path, Transform parent, string generated, Dictionary<string, Material> materials, bool collision)
        {
            var floors = new List<Collider>();
            try
            {
            using (var r = new BinaryReader(OpenGeometry(path), Encoding.UTF8))
            {
                if (Encoding.ASCII.GetString(r.ReadBytes(4)) != "JYWM" || r.ReadInt32() != 1) throw new InvalidDataException(path);
                int count = r.ReadInt32();
                if (count < 1 || count > 20000) throw new InvalidDataException("Invalid mesh count.");
                for (int b = 0; b < count; b++)
                {
                    string group = ReadName(r);
                    string material = ReadName(r);
                    int vc = r.ReadInt32(), ic = r.ReadInt32();
                    if (vc < 3 || vc > 5000000 || ic < 3 || ic > 20000000 || ic % 3 != 0) throw new InvalidDataException("Mesh size is invalid");
                    if (!collision && !materials.ContainsKey(material)) throw new InvalidDataException("Undefined material: " + material);
                    var vertices = new Vector3[vc]; var uv = new Vector2[vc]; var colors = new Color32[vc]; var triangles = new int[ic];
                    for (int i = 0; i < vc; i++) { float x = r.ReadSingle(), y = r.ReadSingle(), z = r.ReadSingle(); if (!IsFinite(x) || !IsFinite(y) || !IsFinite(z)) throw new InvalidDataException("Non-finite vertex in " + group);
                        vertices[i] = new Vector3(x, z, y); }
                    for (int i = 0; i < vc; i++) {
                        float u = r.ReadSingle(), v = r.ReadSingle();
                        if (!IsFinite(u) || !IsFinite(v)) throw new InvalidDataException("Non-finite UV in " + group);
                        uv[i] = new Vector2(u, v);
                    }
                    for (int i = 0; i < vc; i++) colors[i] = new Color32(r.ReadByte(), r.ReadByte(), r.ReadByte(), r.ReadByte());
                    for (int i = 0; i < ic; i += 3) {
                        int a = r.ReadInt32(), bIndex = r.ReadInt32(), c = r.ReadInt32();
                        if (a < 0 || bIndex < 0 || c < 0 || a >= vc || bIndex >= vc || c >= vc)
                            throw new InvalidDataException("Triangle index out of range in " + group);
                        triangles[i] = a; triangles[i + 2] = bIndex; triangles[i + 1] = c;
                    }
                    var mesh = new Mesh { name = group + "_" + material, indexFormat = vc > 65535 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                    mesh.vertices = vertices; mesh.triangles = triangles; mesh.uv = uv; mesh.colors32 = colors;
                    mesh.RecalculateNormals(); mesh.RecalculateBounds();
                    if (!collision) mesh.RecalculateTangents();
                    bool landscape = group.StartsWith("Landscape/", StringComparison.Ordinal);
                    bool tree = group.StartsWith("Tree/", StringComparison.Ordinal);
                    bool foliage = materials.ContainsKey(material) && materials[material].shader.name == "TreeTopYokocho/Foliage";
                    bool beacon = materials.ContainsKey(material) && materials[material].shader.name == "TreeTopYokocho/Beacon";
                    bool cloud = materials.ContainsKey(material) && materials[material].shader.name == "TreeTopYokocho/CloudSea";
                    if (cloud) { var bounds = mesh.bounds; bounds.Expand(new Vector3(0, .30f, 0)); mesh.bounds = bounds; }
                    bool animated = foliage || beacon || cloud || (materials.ContainsKey(material) && materials[material].shader.name == "TreeTopYokocho/Water");
                    bool lightmapped = !collision && !landscape && !tree && !animated;
                    if (lightmapped && !Unwrapping.GenerateSecondaryUVSet(mesh)) throw new InvalidOperationException("Lightmap UV unwrap failed: " + group);
                    // Keep collision mesh coordinates exact; compress only the visual asset.
                    if (!collision) MeshUtility.SetMeshCompression(mesh, ModelImporterMeshCompression.Low);
                    string filename = (collision ? "C_" : "V_") + b.ToString("D3") + ".asset";
                    AssetDatabase.CreateAsset(mesh, generated + "/Meshes/" + filename);
                    bool safe = group.StartsWith("Safety/", StringComparison.Ordinal);
                    bool walkable = group.StartsWith("Floors/", StringComparison.Ordinal) || group.StartsWith("Ramps/", StringComparison.Ordinal);
                    var go = new GameObject((safe ? "Safety_" : (walkable ? "Floor_" : "Mesh_")) + group.Replace('/', '_') + "_" + material);
                    go.transform.SetParent(Group(parent, (collision ? "Collision/" : "Visuals/") + group), false);
                    go.isStatic = true;
                    if (collision)
                    {
                        go.layer = safe ? BarrierLayer : FloorLayer;
                        var collider = go.AddComponent<MeshCollider>();
                        collider.convex = false; collider.isTrigger = false;
                        collider.cookingOptions = MeshColliderCookingOptions.CookForFasterSimulation
                            | MeshColliderCookingOptions.EnableMeshCleaning | MeshColliderCookingOptions.WeldColocatedVertices
                            | MeshColliderCookingOptions.UseFastMidphase;
                        collider.sharedMesh = mesh;
                        if (walkable) floors.Add(collider);
                        // Deliberately no MeshFilter or Renderer on safety walls.
                    }
                    else
                    {
                        go.AddComponent<MeshFilter>().sharedMesh = mesh;
                        var renderer = go.AddComponent<MeshRenderer>(); renderer.sharedMaterial = materials[material];
                        renderer.shadowCastingMode = landscape || beacon || cloud ? ShadowCastingMode.Off : (foliage ? ShadowCastingMode.TwoSided : ShadowCastingMode.On);
                        renderer.receiveShadows = !cloud;
                        renderer.lightProbeUsage = beacon || cloud ? LightProbeUsage.Off : LightProbeUsage.BlendProbes;
                        renderer.reflectionProbeUsage = landscape || foliage || beacon || cloud ? ReflectionProbeUsage.Off : ReflectionProbeUsage.Simple;
                        if (lightmapped) {
                            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.ContributeGI | StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic);
                            renderer.receiveGI = ReceiveGI.Lightmaps;
                            // Dense small decor should not each consume a full-density chart.
                            renderer.scaleInLightmap = group.StartsWith("LanternStrings/") || group.StartsWith("Railings/") ? .35f : .7f;
                        } else {
                            // Animated leaves/water must not be marked static occluders.
                            StaticEditorFlags flags = animated ? 0 : StaticEditorFlags.BatchingStatic;
                            if (tree) flags |= StaticEditorFlags.ContributeGI;
                            GameObjectUtility.SetStaticEditorFlags(go, flags);
                            renderer.receiveGI = ReceiveGI.LightProbes;
                        }
                    }
                }
                if (r.BaseStream.ReadByte() != -1) throw new InvalidDataException("Unexpected mesh payload trailing bytes");
            }
            }
            catch (Exception e) when (e is IOException || e is InvalidDataException)
            {
                throw new InvalidDataException("Could not read geometry " + path + ". Recheck the manifest, gzip integrity and complete contiguous shard set. " + e.Message, e);
            }
            return floors;
        }

        static bool IsFinite(float value) { return !float.IsNaN(value) && !float.IsInfinity(value); }

        static void BindTexture(Material material, string property, string filename, bool normal, bool srgb)
        {
            if (string.IsNullOrEmpty(filename) || !material.HasProperty(property)) return;
            string path = Root + "/Textures/" + filename;
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (importer == null) throw new FileNotFoundException(path);
            if (ImportedTextures.Add(path))
            {
                bool atlas = filename == "signs.png" || filename == "menus.png" || filename == "leaf.png" || filename == "foliage_spray.png";
                bool cutout = filename == "leaf.png" || filename == "foliage_spray.png";
                bool terrain = filename.IndexOf("rocky_terrain", StringComparison.OrdinalIgnoreCase) >= 0;
                int resolution = srgb && !normal && !terrain ? 2048 : 1024;
                importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
                importer.sRGBTexture = srgb && !normal;
                importer.mipmapEnabled = true;
                importer.isReadable = false;
                importer.alphaIsTransparency = cutout;
                importer.mipMapsPreserveCoverage = cutout;
                if (cutout) importer.alphaTestReferenceValue = .4f;
                importer.wrapMode = atlas ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
                importer.anisoLevel = 8;
                importer.maxTextureSize = resolution;
                importer.textureCompression = TextureImporterCompression.CompressedHQ;
                importer.crunchedCompression = false; // BC5 / BC7 do not use Crunch.
                var windows = importer.GetPlatformTextureSettings("Standalone");
                windows.name = "Standalone"; windows.overridden = true; windows.maxTextureSize = resolution;
                windows.format = normal ? TextureImporterFormat.BC5 : TextureImporterFormat.BC7;
                windows.textureCompression = TextureImporterCompression.CompressedHQ;
                windows.crunchedCompression = false; windows.compressionQuality = 80;
                importer.SetPlatformTextureSettings(windows);
                importer.SaveAndReimport();
            }
            material.SetTexture(property, AssetDatabase.LoadAssetAtPath<Texture2D>(path));
        }

        static void ConfigureEnvironment(Transform world, string generated, Manifest manifest)
        {
            PlayerSettings.colorSpace = ColorSpace.Linear;
            QualitySettings.shadows = UnityEngine.ShadowQuality.All;
            QualitySettings.shadowResolution = ShadowResolution.High;
            QualitySettings.shadowDistance = 65;
            QualitySettings.shadowCascades = 2;
            QualitySettings.pixelLightCount = 2;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(.16f, .22f, .36f);
            RenderSettings.ambientEquatorColor = new Color(.24f, .27f, .33f);
            RenderSettings.ambientGroundColor = new Color(.10f, .085f, .065f);
            RenderSettings.ambientIntensity = 1;
            RenderSettings.fog = true; RenderSettings.fogMode = FogMode.ExponentialSquared;
            RenderSettings.fogDensity = .00028f; RenderSettings.fogColor = new Color(.16f, .22f, .31f);
            var skyShader = Shader.Find("TreeTopYokocho/BlueHourSky");
            if (skyShader == null) throw new InvalidOperationException("The blue-hour sky shader has not imported.");
            var sky = new Material(skyShader);
            AssetDatabase.CreateAsset(sky, generated + "/Materials/Sky.mat"); RenderSettings.skybox = sky;
            var moon = new GameObject("BlueHour_Key").AddComponent<Light>();
            moon.transform.SetParent(world, false); moon.type = LightType.Directional;
            moon.transform.rotation = Quaternion.Euler(26, -38, 0); moon.color = new Color(.62f, .75f, 1); moon.intensity = .70f;
            moon.shadows = LightShadows.Soft; moon.shadowBias = .02f; moon.shadowNormalBias = .12f;
            moon.lightmapBakeType = LightmapBakeType.Mixed; RenderSettings.sun = moon;
            var fill = new GameObject("Sunset_WarmFill").AddComponent<Light>();
            fill.transform.SetParent(world, false); fill.type = LightType.Directional;
            fill.transform.rotation = Quaternion.Euler(8, 138, 0); fill.color = new Color(1, .55f, .28f); fill.intensity = .18f;
            fill.shadows = LightShadows.None; fill.lightmapBakeType = LightmapBakeType.Baked;
            Transform lightRoot = Group(world, "Lighting/Lanterns");
            for (int i = 0; i < manifest.lights.Length; i++)
            {
                LightSpec spec = manifest.lights[i];
                var l = new GameObject("Lantern_" + i.ToString("D3")).AddComponent<Light>();
                l.transform.SetParent(lightRoot, false); l.transform.position = U(spec.position);
                l.type = LightType.Point; l.color = new Color(1, .52f, .18f); l.range = spec.range * 1.25f;
                l.intensity = spec.strength * 1.65f; l.bounceIntensity = 1.6f;
                l.lightmapBakeType = LightmapBakeType.Baked;
                l.renderMode = LightRenderMode.Auto;
                l.shadows = LightShadows.Soft; // Baked shadows only; no runtime point-light shadow maps.
                l.shadowResolution = LightShadowResolution.Medium; l.shadowBias = .025f; l.shadowNormalBias = .10f;
            }
            var settings = new LightingSettings { name = "Yokocho_PC_Balanced_Bake" };
            settings.bakedGI = true; settings.realtimeGI = false;
            settings.lightmapper = LightingSettings.Lightmapper.ProgressiveCPU;
            settings.lightmapResolution = 12; settings.lightmapMaxSize = 2048;
            settings.directionalityMode = LightmapsMode.NonDirectional;
            settings.compressLightmaps = true; settings.autoGenerate = false;
            settings.lightmapPadding = 4; settings.ao = true; settings.aoMaxDistance = 1.0f;
            settings.aoExponentIndirect = 1.15f; settings.aoExponentDirect = .35f;
            settings.mixedBakeMode = MixedLightingMode.IndirectOnly;
            settings.directSampleCount = 64; settings.indirectSampleCount = 256; settings.environmentSampleCount = 128;
            AssetDatabase.CreateAsset(settings, generated + "/HighDetailLighting.lighting");
            Lightmapping.lightingSettings = settings;
            var probes = new GameObject("Avatar_LightProbes").AddComponent<LightProbeGroup>(); probes.transform.SetParent(world, false);
            var positions = new List<Vector3>();
            for (int i = 0; i < manifest.floorTests.Length; i += 5) {
                Vector3 p = U(manifest.floorTests[i].position);
                positions.Add(p + Vector3.up * .45f); positions.Add(p + Vector3.up * 1.75f); positions.Add(p + Vector3.up * 2.65f);
            }
            probes.probePositions = positions.ToArray();
            Vector3[] locations = { new Vector3(0, 42, 0), new Vector3(0, 36, -26), new Vector3(29, 42, 0), new Vector3(0, 48, 26), new Vector3(-25, 54, 22), new Vector3(0, 1, 80), new Vector3(-9, 114, -18) };
            float alleyLift = manifest.altitudeProfile != null ? manifest.altitudeProfile.addedAlleyHeight : 0;
            for (int i = 0; i < 5; i++) locations[i].y += alleyLift;
            locations[6].y += alleyLift; // Crown observatory, separate from the fixed ground probe.
            for (int i = 0; i < locations.Length; i++) {
                var probe = new GameObject("Reflection_" + i).AddComponent<ReflectionProbe>(); probe.transform.SetParent(world, false);
                probe.transform.position = locations[i]; probe.mode = ReflectionProbeMode.Baked;
                probe.resolution = 128; probe.hdr = true; probe.boxProjection = true;
                probe.size = i == 5 ? new Vector3(500, 40, 500) : (i == 6 ? new Vector3(60, 18, 60) : new Vector3(45, 18, 45));
                probe.blendDistance = 8; probe.farClipPlane = 2400; probe.intensity = .9f;
            }
            ConfigureSteam(world, generated, manifest);
            var audio = new GameObject("Quiet_CanopyWind").AddComponent<AudioSource>();
            audio.transform.SetParent(world, false); audio.clip = AssetDatabase.LoadAssetAtPath<AudioClip>(Root + "/Audio/CanopyWind.wav");
            audio.loop = true; audio.playOnAwake = true; audio.spatialBlend = 0; audio.volume = .12f;
        }

        static void Parameter(object effect, string name, object value)
        {
            if (effect == null) throw new ArgumentNullException("effect");
            var parameterField = effect.GetType().GetField(name);
            if (parameterField == null) throw new MissingFieldException(effect.GetType().Name, name);
            object parameter = parameterField.GetValue(effect);
            SetMember(parameter, "overrideState", true, true);
            var field = parameter.GetType().GetField("value");
            if (field == null) throw new MissingFieldException(parameter.GetType().Name, "value");
            object converted = field.FieldType.IsEnum && value is string ? Enum.Parse(field.FieldType, (string)value) : ConvertValue(value, field.FieldType);
            field.SetValue(parameter, converted);
        }

        static void ConfigurePostProcessing(Transform world, string generated, Camera camera)
        {
            if (camera == null) throw new InvalidOperationException("A reference camera is required for post processing.");
            Type volumeType = FindType("UnityEngine.Rendering.PostProcessing.PostProcessVolume");
            Type profileType = FindType("UnityEngine.Rendering.PostProcessing.PostProcessProfile");
            Type layerType = FindType("UnityEngine.Rendering.PostProcessing.PostProcessLayer");
            Type resourceType = FindType("UnityEngine.Rendering.PostProcessing.PostProcessResources");
            if (volumeType == null || profileType == null || layerType == null || resourceType == null) {
                Debug.LogWarning("For the intended ACES / bloom look, install Unity Post Processing via Package Manager, then run 6 - Set Up Post Processing. Core world generation is complete.");
                return;
            }
            string resourceGuid = AssetDatabase.FindAssets("t:PostProcessResources").FirstOrDefault();
            if (string.IsNullOrEmpty(resourceGuid)) { Debug.LogWarning("Post Processing resources were not found. Complete package import and run menu 6 again."); return; }
            var resource = AssetDatabase.LoadAssetAtPath(AssetDatabase.GUIDToAssetPath(resourceGuid), resourceType);
            Type bloomType = FindType("UnityEngine.Rendering.PostProcessing.Bloom");
            Type gradingType = FindType("UnityEngine.Rendering.PostProcessing.ColorGrading");
            MethodInfo add = profileType.GetMethod("AddSettings", new [] { typeof(Type) });
            if (add == null || bloomType == null || gradingType == null || resource == null)
                throw new InvalidOperationException("The installed PPS v2 API/resources are incomplete.");
            var profile = ScriptableObject.CreateInstance(profileType); profile.name = "Yokocho_Filmic";
            string profilePath = AssetDatabase.GenerateUniqueAssetPath(generated + "/Yokocho_Filmic.asset");
            AssetDatabase.CreateAsset(profile, profilePath);
            var bloom = add.Invoke(profile, new object[] { bloomType });
            Parameter(bloom, "enabled", true); Parameter(bloom, "intensity", .55f); Parameter(bloom, "threshold", 1.15f); Parameter(bloom, "softKnee", .65f);
            var grading = add.Invoke(profile, new object[] { gradingType });
            Parameter(grading, "enabled", true); Parameter(grading, "gradingMode", "HighDefinitionRange"); Parameter(grading, "tonemapper", "ACES");
            Parameter(grading, "postExposure", .25f); Parameter(grading, "temperature", 3f); Parameter(grading, "saturation", -5f);
            AssetDatabase.AddObjectToAsset((UnityEngine.Object)bloom, profile); AssetDatabase.AddObjectToAsset((UnityEngine.Object)grading, profile);
            var layer = camera.GetComponent(layerType) ?? camera.gameObject.AddComponent(layerType);
            SetMember(layer, "volumeLayer", (LayerMask)1, true); SetMember(layer, "volumeTrigger", camera.transform, true);
            var init = layerType.GetMethod("Init", new [] { resourceType });
            if (init != null) init.Invoke(layer, new [] { resource });
            // Create the completion marker only after camera setup succeeds, so
            // an optional PPS failure can be retried from menu 6.
            var volumeGO = new GameObject("Filmic_PostProcessing"); volumeGO.transform.SetParent(world, false); volumeGO.layer = 0;
            var volume = volumeGO.AddComponent(volumeType);
            SetMember(volume, "isGlobal", true, true); SetMember(volume, "weight", 1f, true); SetMember(volume, "priority", 0f, true); SetMember(volume, "sharedProfile", profile, true);
            EditorUtility.SetDirty(profile); EditorUtility.SetDirty(layer); AssetDatabase.SaveAssets();
        }

        [MenuItem("Tools/TreeTop Yokocho/6 - Set Up Post Processing")]
        public static void SetupPostProcessing()
        {
            var root = GameObject.Find("TreeTopYokocho_v2");
            if (root == null) throw new InvalidOperationException("Build/open the v2 scene first.");
            if (root.transform.Find("Filmic_PostProcessing") != null) { Debug.Log("Post Processing already exists. Edit the saved profile to adjust it."); return; }
            string scenePath = SceneManager.GetActiveScene().path;
            if (string.IsNullOrEmpty(scenePath)) throw new InvalidOperationException("Save the generated scene first.");
            string folder = Path.GetDirectoryName(scenePath).Replace('\\', '/');
            ConfigurePostProcessing(root.transform, folder, root.GetComponentInChildren<Camera>(true));
            EditorSceneManager.SaveOpenScenes();
        }

        static void ConfigureSteam(Transform world, string generated, Manifest manifest)
        {
            if (manifest.steam == null) return;
            var steamShader = Shader.Find("TreeTopYokocho/Steam");
            if (steamShader == null) throw new InvalidOperationException("Steam shader is missing.");
            var material = new Material(steamShader) { name = "WarmSteam" };
            AssetDatabase.CreateAsset(material, generated + "/Materials/Steam.mat");
            foreach (var s in manifest.steam) {
                var go = new GameObject("Steam_" + s.id); go.transform.SetParent(Group(world, "Atmosphere/Steam"), false);
                go.transform.position = U(s.position); go.transform.rotation = Quaternion.Euler(-90, 0, 0);
                var ps = go.AddComponent<ParticleSystem>(); ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
                var main = ps.main; main.loop = true; main.playOnAwake = true; main.simulationSpace = ParticleSystemSimulationSpace.World;
                main.startLifetime = new ParticleSystem.MinMaxCurve(1.7f, 3.1f); main.startSpeed = new ParticleSystem.MinMaxCurve(.22f, .40f);
                main.startSize = new ParticleSystem.MinMaxCurve(.20f, .42f); main.startColor = new Color(.85f, .80f, .70f, .18f); main.maxParticles = 45;
                var emission = ps.emission; emission.rateOverTime = 9;
                var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Cone; shape.angle = 8; shape.radius = .10f;
                var noise = ps.noise; noise.enabled = true; noise.strength = .065f; noise.frequency = .45f; noise.scrollSpeed = .20f;
                var size = ps.sizeOverLifetime; size.enabled = true; size.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, .6f, 1, 2.4f));
                var color = ps.colorOverLifetime; color.enabled = true; var gradient = new Gradient();
                gradient.SetKeys(new [] { new GradientColorKey(Color.white,0), new GradientColorKey(Color.white,1) },
                    new [] { new GradientAlphaKey(0,0), new GradientAlphaKey(1,.2f), new GradientAlphaKey(0,1) });
                color.color = gradient;
                var renderer = ps.GetComponent<ParticleSystemRenderer>(); renderer.sharedMaterial = material;
                renderer.renderMode = ParticleSystemRenderMode.Billboard; renderer.shadowCastingMode = ShadowCastingMode.Off;
                renderer.receiveShadows = false; renderer.lightProbeUsage = LightProbeUsage.Off;
                renderer.reflectionProbeUsage = ReflectionProbeUsage.Off;
                ps.Play();
            }
        }

        [MenuItem("Tools/TreeTop Yokocho/4 - Bake High Quality Lighting")]
        public static void BakeLighting()
        {
            if (Lightmapping.isRunning) throw new InvalidOperationException("A lighting bake is already running.");
            if (GameObject.Find("TreeTopYokocho_v2") == null) throw new InvalidOperationException("Build/open the v2 scene first.");
            EditorSceneManager.SaveOpenScenes();
            if (!Lightmapping.BakeAsync()) throw new InvalidOperationException("Unity could not start the lightmap bake. Inspect the Console.");
            Debug.Log("Balanced PC lightmap and light probe bake started. Wait for completion, then run 5 - Bake Reflections.");
        }

        [MenuItem("Tools/TreeTop Yokocho/5 - Bake Reflections")]
        public static void BakeReflections()
        {
            if (Lightmapping.isRunning) throw new InvalidOperationException("Wait for the lightmap bake to finish first.");
            var root = GameObject.Find("TreeTopYokocho_v2");
            if (root == null) throw new InvalidOperationException("Build/open the v2 scene first.");
            string scenePath = SceneManager.GetActiveScene().path;
            if (string.IsNullOrEmpty(scenePath)) throw new InvalidOperationException("Save the generated scene first.");
            string folder = Path.GetDirectoryName(scenePath).Replace('\\', '/') + "/Reflections";
            Directory.CreateDirectory(folder); AssetDatabase.Refresh();
            foreach (var probe in root.GetComponentsInChildren<ReflectionProbe>()) {
                string path = folder + "/" + probe.name + ".exr";
                if (!Lightmapping.BakeReflectionProbe(probe, path)) Debug.LogError("Reflection bake failed: " + probe.name);
                else { AssetDatabase.ImportAsset(path); probe.bakedTexture = AssetDatabase.LoadAssetAtPath<Texture>(path); }
            }
            EditorSceneManager.SaveOpenScenes(); AssetDatabase.SaveAssets();
        }

        static Transform Group(Transform root, string path)
        {
            Transform current = root;
            foreach (string part in path.Split('/'))
            {
                var child = current.Find(part);
                if (child == null) { child = new GameObject(part).transform; child.SetParent(current, false); }
                current = child;
            }
            return current;
        }

        static Type FindType(string name)
        {
            foreach (var a in AppDomain.CurrentDomain.GetAssemblies()) { var t = a.GetType(name, false); if (t != null) return t; }
            return null;
        }
        static object ConvertValue(object value, Type type)
        {
            if (type.IsInstanceOfType(value)) return value;
            if (type.IsEnum) return value is string ? Enum.Parse(type, (string)value, true) : Enum.ToObject(type, Convert.ToInt32(value));
            if (type == typeof(GameObject) && value is Component component) return component.gameObject;
            return Convert.ChangeType(value, type);
        }
        // These are SDK members, resolved by exact case-insensitive names for SDK
        // minor-version tolerance. Critical fields fail loudly if unavailable.
        static void SetMember(object target, string name, object value, bool required)
        {
            const BindingFlags flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.IgnoreCase;
            var type = target.GetType();
            var field = type.GetField(name, flags);
            if (field != null) { field.SetValue(target, ConvertValue(value, field.FieldType)); return; }
            var prop = type.GetProperty(name, flags);
            if (prop != null && prop.CanWrite) { prop.SetValue(target, ConvertValue(value, prop.PropertyType)); return; }
            if (required) throw new MissingMemberException(type.FullName, name);
        }
        static void ConfigureInteraction(UdonSharpBehaviour proxy, string text, float range)
        {
            var udon = UdonSharpEditorUtility.GetBackingUdonBehaviour(proxy);
            if (udon == null) throw new InvalidOperationException("UdonSharp did not create the backing UdonBehaviour.");
            SetMember(udon, "interactText", text, false);
            SetMember(udon, "proximity", range, false);
            EditorUtility.SetDirty(udon);
        }

        static bool FloorBelow(Vector3 point, Transform root)
        {
            RaycastHit hit;
            return Physics.Raycast(point + Vector3.up * .5f, Vector3.down, out hit, 1.2f,
                1 << FloorLayer, QueryTriggerInteraction.Ignore)
                && hit.collider.name.StartsWith("Floor_", StringComparison.Ordinal)
                && hit.collider.transform.IsChildOf(root);
        }

        static bool HitsBarrier(Vector3 start, Vector3 end, Transform root)
        {
            Vector3 delta = end - start;
            if (delta.sqrMagnitude < .000001f) return false;
            RaycastHit hit;
            return Physics.Raycast(start, delta.normalized, out hit, delta.magnitude,
                1 << BarrierLayer, QueryTriggerInteraction.Ignore)
                && hit.collider.name.StartsWith("Safety_", StringComparison.Ordinal)
                && hit.collider.transform.IsChildOf(root);
        }

        [MenuItem("Tools/TreeTop Yokocho/2 - Audit Physics")]
        public static void Audit()
        {
            var manifest = ReadManifest();
            var root = GameObject.Find("TreeTopYokocho_v2");
            if (root == null) throw new InvalidOperationException("Build or open the generated scene first.");
            Physics.SyncTransforms();
            int checks = 0, barriers = 0;
            var errors = new List<string>();
            checks += 3;
            if (LayerMask.LayerToName(BarrierLayer) != "Interactive" || LayerMask.LayerToName(LocalPlayerLayer) != "PlayerLocal")
                errors.Add("VRChat built-in layers are not configured. Run the SDK project setup before testing.");
            if (Physics.GetIgnoreLayerCollision(FloorLayer, LocalPlayerLayer)) errors.Add("Default floors do not collide with PlayerLocal.");
            if (Physics.GetIgnoreLayerCollision(BarrierLayer, LocalPlayerLayer)) errors.Add("Invisible barriers do not collide with PlayerLocal.");
            foreach (var collider in root.GetComponentsInChildren<Collider>(true))
            {
                if (!collider.name.StartsWith("Safety_", StringComparison.Ordinal)) continue;
                checks++; barriers++;
                var meshCollider = collider as MeshCollider;
                if (!collider.enabled || !collider.gameObject.activeInHierarchy || collider.isTrigger
                    || collider.gameObject.layer != BarrierLayer || collider.GetComponentsInChildren<Renderer>(true).Length > 0
                    || collider.GetComponent<MeshFilter>() != null || meshCollider == null || meshCollider.sharedMesh == null
                    || meshCollider.convex || collider.attachedRigidbody != null)
                    errors.Add("Invalid renderer-free static barrier: " + collider.name);
            }
            if (barriers == 0) errors.Add("No fall barriers found.");
            if (manifest.floorTests.Length == 0 || manifest.wallTests.Length == 0) errors.Add("Safety test arrays must not be empty.");
            foreach (var test in manifest.floorTests)
            {
                checks++;
                RaycastHit hit;
                var point = U(test.position);
                if (!Physics.Raycast(point + Vector3.up * .75f, Vector3.down, out hit, 1.65f, 1 << FloorLayer, QueryTriggerInteraction.Ignore)
                    || !hit.collider.name.StartsWith("Floor_", StringComparison.Ordinal) || !hit.collider.transform.IsChildOf(root.transform))
                    errors.Add("Floor probe failed: " + test.id + " at " + point);
            }
            foreach (var test in manifest.wallTests)
            {
                checks += 2;
                Vector3 start = U(test.start), end = U(test.end);
                if (!HitsBarrier(start, end, root.transform)) errors.Add("Barrier outward probe failed at " + start);
                if (!HitsBarrier(end, start, root.transform)) errors.Add("Barrier inward probe failed at " + end);
            }
            foreach (var seat in manifest.stations)
            {
                checks++;
                if (!FloorBelow(U(seat.exit), root.transform)) errors.Add("Seat exit is not over a safe floor: " + seat.name);
            }
            foreach (var spawn in manifest.spawns)
            {
                checks++;
                if (!FloorBelow(U(spawn.position), root.transform)) errors.Add("Spawn is not over a safe floor: " + U(spawn.position));
            }
            foreach (var lift in manifest.teleports)
            {
                checks++;
                if (!FloorBelow(U(lift.destination), root.transform)) errors.Add("Lift destination is not over a safe floor: " + lift.name);
            }
            var seats = root.GetComponentsInChildren<YokochoSeat>(true);
            var lifts = root.GetComponentsInChildren<YokochoTeleport>(true);
            var recovery = root.GetComponentInChildren<YokochoSafety>(true);
            if (seats.Length != manifest.stations.Length) errors.Add("Station proxy count differs from the manifest.");
            if (lifts.Length != manifest.teleports.Length) errors.Add("Lift proxy count differs from the manifest.");
            foreach (var seat in seats)
                if (seat.recovery != recovery || seat.exitPoint == null) errors.Add("Seat recovery wiring is missing: " + seat.name);
            foreach (var lift in lifts)
                if (lift.recovery != recovery || lift.destination == null) errors.Add("Lift recovery wiring is missing: " + lift.name);
            if (recovery == null || recovery.arrival == null || recovery.walkableFloors == null || recovery.walkableFloors.Length == 0)
                errors.Add("Fall recovery references are missing.");
            var lines = new List<string> {
                "Tree-top Yokocho Unity physics audit", "UTC: " + DateTime.UtcNow.ToString("O"),
                "Scope: Unity scene configuration and raycasts only; NOT CharacterController, room-scale VR or multiplayer validation.",
                "Checks: " + checks, "Barriers: " + barriers, "Errors: " + errors.Count };
            lines.AddRange(errors);
            Directory.CreateDirectory(Root + "/Generated");
            File.WriteAllLines(Root + "/Generated/PhysicsAudit.txt", lines, Encoding.UTF8);
            AssetDatabase.Refresh();
            if (errors.Count > 0) Debug.LogError(string.Join("\n", lines.Take(25)));
            else Debug.Log("Physics audit passed: " + checks + " checks. ClientSim and VRChat Build & Test are still required, including walking/jumping at stairs, holes and deck edges.");
        }

        [MenuItem("Tools/TreeTop Yokocho/7 - Audit PC Budget")]
        public static void AuditBudget()
        {
            var root = GameObject.Find("TreeTopYokocho_v2");
            if (root == null) throw new InvalidOperationException("Build or open the generated scene first.");
            var renderers = root.GetComponentsInChildren<Renderer>(true);
            var lights = root.GetComponentsInChildren<Light>(true);
            var meshes = root.GetComponentsInChildren<MeshFilter>(true).Select(x => x.sharedMesh).Where(x => x != null).Distinct().ToArray();
            var materials = renderers.SelectMany(x => x.sharedMaterials).Where(x => x != null).Distinct().ToArray();
            var textures = new HashSet<Texture>();
            long triangles = 0;
            foreach (var mesh in meshes)
                for (int i = 0; i < mesh.subMeshCount; i++) triangles += mesh.GetIndexCount(i) / 3;
            foreach (var material in materials)
                foreach (string property in material.GetTexturePropertyNames()) {
                    Texture texture = material.GetTexture(property); if (texture != null) textures.Add(texture);
                }
            foreach (var map in LightmapSettings.lightmaps) {
                if (map.lightmapColor != null) textures.Add(map.lightmapColor);
                if (map.lightmapDir != null) textures.Add(map.lightmapDir);
                if (map.shadowMask != null) textures.Add(map.shadowMask);
            }
            foreach (var probe in root.GetComponentsInChildren<ReflectionProbe>(true))
                if (probe.bakedTexture != null) textures.Add(probe.bakedTexture);
            long textureMemory = textures.Sum(x => UnityEngine.Profiling.Profiler.GetRuntimeMemorySizeLong(x));
            int liveLights = lights.Count(x => x.lightmapBakeType != LightmapBakeType.Baked);
            int livePointShadows = lights.Count(x => x.type == LightType.Point && x.shadows != LightShadows.None && x.lightmapBakeType != LightmapBakeType.Baked);
            var warnings = new List<string>();
            if (triangles > 1500000) warnings.Add("Scene exceeds this project's 1.5M-triangle review threshold. Check visible triangles from each deck and profile in VR; this is not an SDK limit.");
            if (renderers.Length > 400) warnings.Add("More than 400 renderers: inspect actual batches and SetPass calls in the Unity Profiler; renderer count is not draw-call count.");
            if (liveLights > 2 || livePointShadows > 0) warnings.Add("Realtime lighting exceeds the balanced PC budget.");
            if (LightmapSettings.lightmaps.Length == 0) warnings.Add("Lighting is not baked. Baked lanterns cannot provide their intended runtime illumination yet. Complete menu 4, then menu 5.");
            if (root.GetComponentsInChildren<ReflectionProbe>(true).Any(x => x.bakedTexture == null)) warnings.Add("At least one reflection probe has not been baked.");
            if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.StandaloneWindows64) warnings.Add("Select Windows x86_64 before the SDK build. This package targets PC, not Android.");
            foreach (var shader in materials.Select(x => x.shader).Where(x => x != null).Distinct())
                if (ShaderUtil.ShaderHasError(shader)) warnings.Add("Unity reports a shader error: " + shader.name);
            var lines = new List<string> {
                "Tree-top Yokocho PC budget audit", "UTC: " + DateTime.UtcNow.ToString("O"),
                "Scene mesh triangles: " + triangles, "Renderers (including particles): " + renderers.Length,
                "Unique materials: " + materials.Length, "Baked-only lights: " + lights.Count(x => x.lightmapBakeType == LightmapBakeType.Baked),
                "Realtime/mixed lights: " + liveLights, "Realtime point shadow lights: " + livePointShadows,
                "Lightmap atlases: " + LightmapSettings.lightmaps.Length, "Referenced loaded texture memory MiB: " + (textureMemory / 1048576.0).ToString("F2"),
                "Download target: approximately 50 MB. ACTUAL SDK BUNDLE SIZE NOT MEASURED BY THIS AUDIT.",
                "Texture runtime memory and source/archive sizes are not VRChat download size. Record the SDK's final build size after lighting/reflection baking.",
                "Warnings: " + warnings.Count };
            lines.AddRange(warnings);
            Directory.CreateDirectory(Root + "/Generated");
            File.WriteAllLines(Root + "/Generated/PCBudgetAudit.txt", lines, Encoding.UTF8);
            AssetDatabase.Refresh();
            Debug.Log(string.Join("\n", lines));
        }

        [MenuItem("Tools/TreeTop Yokocho/3 - Show Fall Barriers")]
        public static void ShowBarriers() { SetBarrierSelection(); }
        static void SetBarrierSelection()
        {
            var root = GameObject.Find("TreeTopYokocho_v2");
            if (root == null) return;
            Selection.objects = root.GetComponentsInChildren<Collider>(true).Where(x => x.name.StartsWith("Safety_", StringComparison.Ordinal)).Select(x => x.gameObject).ToArray();
            SceneView.RepaintAll();
        }
    }
}
#endif

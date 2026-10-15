#if UNITY_EDITOR && !COMPILER_UDONSHARP
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace TreeTopYokocho.Integration.Editor
{
    // Editor-only additive material overlay. Never modifies baseline source assets,
    // meshes, UVs, shader keywords, colliders, light settings or interaction objects.
    public static class OriginalPbrInstaller
    {
        public const string Root = "Assets/TreeTopYokochoOriginalPbr";
        public const string Marker = "OriginalPbr_v1";
        public const string ApprovedPlanSha256 = "a9f1f27025136efba59dd368b844e9e5cfcdecf00dd9ec7bf80b7a9376d9900e";
        const string CoreManifest = "Assets/TreeTopYokocho/Data/WorldManifest.json";
        const string CoreManifestSha256 = "aa513b1c948ba9353a08c3d9eea6f4852f5d8ffa05715f036ea27d19f003d466";
        const string OriginalPrefix = "Assets/TreeTopYokocho/Generated/";

        [Serializable] public class FilePin { public string path, sha256; }
        [Serializable] public class Slot { public string property, originalPath, replacementPath; }
        [Serializable] public class MaterialRow { public string name; public int expectedRendererCount; public Slot[] slots; public bool calibrateParallax; public float originalParallax, replacementParallax; }
        [Serializable] public class Plan { public int schema; public string baselineManifestSha256; public FilePin[] baselineFiles, maps; public MaterialRow[] materials; }
        [Serializable] public class Receipt { public int schema; public string planSha256, baselineManifestSha256, sceneGuid; public string[] names, originalPaths, clonePaths; public bool unityRuntimeVerified; }

        static string Sha256(byte[] bytes)
        {
            using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
        }
        static string AssetPath(UnityEngine.Object value) { return AssetDatabase.GetAssetPath(value).Replace('\\', '/'); }
        static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
        static bool Under(string path, string prefix)
        {
            return path != null && path.StartsWith(prefix, StringComparison.Ordinal) && !path.Contains("..") && !path.Contains("\\");
        }
        static Plan LoadPlan()
        {
            Require(!ApprovedPlanSha256.StartsWith("UNFROZEN", StringComparison.Ordinal), "Original PBR art/source plan has not been reviewed. Installation is disabled.");
            string path = Root + "/Data/OriginalPbrPlan.json";
            byte[] bytes = File.ReadAllBytes(path);
            Require(Sha256(bytes) == ApprovedPlanSha256, "Original PBR plan differs from the reviewed source package.");
            var plan = JsonUtility.FromJson<Plan>(System.Text.Encoding.UTF8.GetString(bytes));
            Require(plan != null && plan.schema == 1 && plan.baselineManifestSha256 == CoreManifestSha256,
                "Unsupported original PBR plan/baseline.");
            Require(plan.materials != null && plan.materials.Length == 31 && plan.maps != null && plan.maps.Length == 16,
                "Expected exactly 31 material definitions and 16 authored maps.");
            Require(plan.materials.Select(x => x.name).Distinct().Count() == 31 && plan.maps.Select(x => x.path).Distinct().Count() == 16,
                "Duplicate original PBR material/map entries.");
            return plan;
        }

        public static void Preflight()
        {
            var plan = LoadPlan();
            Require(Sha256(File.ReadAllBytes(CoreManifest)) == CoreManifestSha256, "Immutable v2.19 core manifest changed.");
            string combined = "Assets/TreeTopYokocho/Data/VisualMeshes.bytes.gz";
            Require(!File.Exists(combined) || Sha256(File.ReadAllBytes(combined)) == "c5d324af8e0e5ea2ad1ddfb22fa050d24b7652cbe22d26079eb7265b807dee29", "Stale combined visual gzip overrides the verified source shards.");
            foreach (var file in plan.baselineFiles)
            {
                Require(Under(file.path, "Assets/TreeTopYokocho/"), "Unowned baseline pin path.");
                Require(LocalCoreRepairRevision.Matches(file.path, file.sha256, Sha256(File.ReadAllBytes(file.path))),
                    "Baseline source changed outside the supported core repair revision: " + file.path);
            }
            foreach (var file in plan.maps)
            {
                Require(Under(file.path, Root + "/Textures/PBR/"), "Unowned original map path.");
                Require(Sha256(File.ReadAllBytes(file.path)) == file.sha256, "Authored map differs from reviewed bytes: " + file.path);
                var importer = AssetImporter.GetAtPath(file.path) as TextureImporter;
                var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(file.path);
                bool normal = file.path.EndsWith("_normalGL.png", StringComparison.Ordinal);
                bool albedo = file.path.EndsWith("_albedo.png", StringComparison.Ordinal);
                bool rock = file.path.IndexOf("/yokocho_mineral_rock_", StringComparison.Ordinal) >= 0;
                int cap = albedo && !rock ? 2048 : 1024;
                Require(importer != null && texture != null, "Authored texture has not imported: " + file.path);
                Require(importer.textureType == (normal ? TextureImporterType.NormalMap : TextureImporterType.Default)
                    && importer.sRGBTexture == albedo && !importer.flipGreenChannel && !importer.convertToNormalmap && importer.mipmapEnabled && importer.wrapMode == TextureWrapMode.Repeat
                    && importer.maxTextureSize == cap && importer.swizzleR == TextureImporterSwizzle.R && importer.swizzleG == TextureImporterSwizzle.G
                    && importer.swizzleB == TextureImporterSwizzle.B && importer.swizzleA == TextureImporterSwizzle.A, "Reimport original texture with the supplied importer: " + file.path);
                var windows = importer.GetPlatformTextureSettings("Standalone");
                Require(windows.overridden && windows.maxTextureSize == cap && windows.format == (normal ? TextureImporterFormat.BC5 : TextureImporterFormat.BC7),
                    "Standalone compression differs from the reviewed import policy: " + file.path);
            }
            var mapPaths = new HashSet<string>(plan.maps.Select(x => x.path));
            Require(plan.materials.Count(x => x.expectedRendererCount == 0) == 1 && plan.materials.Single(x => x.expectedRendererCount == 0).name == "Moss", "Only the original unused Moss definition may have no renderer.");
            foreach (var row in plan.materials)
            {
                Require(row.expectedRendererCount >= 0, "Invalid renderer count.");
                Require(!string.IsNullOrEmpty(row.name) && !row.name.Contains("/") && !row.name.Contains("\\"), "Invalid material name.");
                Require(row.slots != null && row.slots.Length >= 1 && row.slots.Select(x => x.property).Distinct().Count() == row.slots.Length, "Invalid material slot roster.");
                foreach (var slot in row.slots)
                    Require(new[] { "_MainTex", "_BumpMap", "_ARM", "_HeightMap" }.Contains(slot.property)
                        && Under(slot.originalPath, "Assets/TreeTopYokocho/Textures/PBR/") && mapPaths.Contains(slot.replacementPath), "Unowned texture slot mapping.");
                Require(!row.calibrateParallax || (Mathf.Approximately(row.originalParallax, .014f) && row.replacementParallax > 0 && row.replacementParallax <= .008f),
                    "Unexpected parallax calibration.");
            }
        }

        static GameObject Core(Scene scene)
        {
            Require(scene.IsValid() && scene.isLoaded && !string.IsNullOrEmpty(scene.path), "Generate and save the supported core scene first.");
            var cores = scene.GetRootGameObjects().Where(x => x.name == "TreeTopYokocho_v2").ToArray();
            Require(cores.Length == 1, "Expected exactly one core root in the active scene.");
            var t = cores[0].transform;
            Require(t.position == Vector3.zero && t.rotation == Quaternion.identity && t.localScale == Vector3.one, "Core transform changed.");
            return cores[0];
        }
        static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/'); EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }

        public static void Install()
        {
            Require(!EditorApplication.isPlayingOrWillChangePlaymode, "Exit Play mode before original material installation.");
            Preflight();
            var plan = LoadPlan(); var scene = SceneManager.GetActiveScene(); var core = Core(scene);
            var markers = scene.GetRootGameObjects().Where(x => x.name == Marker).ToArray();
            Require(markers.Length <= 1, "Duplicate original PBR markers; resolve manually.");
            if (markers.Length == 1) { ValidateExisting(plan, scene, core, markers[0]); return; }
            var renderers = core.GetComponentsInChildren<Renderer>(true);
            var originals = new Dictionary<string, Material>();
            string materialDirectory = null;
            // Inspect every target before allocating assets. Changed/foreign materials are never silently replaced.
            foreach (var row in plan.materials.OrderByDescending(x => x.expectedRendererCount))
            {
                var references = renderers.SelectMany(x => x.sharedMaterials).Where(x => x != null && x.name == row.name).ToArray();
                Require(references.Length == row.expectedRendererCount, "Active material slot count changed: " + row.name);
                var matches = references.Distinct().ToArray();
                Require(matches.Length == (row.expectedRendererCount == 0 ? 0 : 1), "Missing/ambiguous original material: " + row.name);
                if (materialDirectory == null)
                {
                    Require(matches.Length == 1, "No active source material identifies the generated directory.");
                    materialDirectory = Path.GetDirectoryName(AssetPath(matches[0])).Replace('\\', '/');
                }
                string originalPath = materialDirectory + "/" + row.name + ".mat";
                var original = AssetDatabase.LoadAssetAtPath<Material>(originalPath);
                Require(original != null && original.name == row.name && (matches.Length == 0 || matches[0] == original), "Missing or mixed generated material directory: " + row.name);
                Require(Under(originalPath, OriginalPrefix) && originalPath.EndsWith("/Materials/" + row.name + ".mat", StringComparison.Ordinal),
                    "Target is not a core-generated material: " + row.name);
                foreach (var slot in row.slots)
                    Require(original.HasProperty(slot.property) && AssetPath(original.GetTexture(slot.property)) == slot.originalPath,
                        "Original texture binding changed: " + row.name + " " + slot.property);
                if (row.calibrateParallax) Require(original.HasProperty("_Parallax") && Mathf.Approximately(original.GetFloat("_Parallax"), row.originalParallax), "Original parallax changed: " + row.name);
                originals.Add(row.name, original);
            }
            var saved = renderers.ToDictionary(x => x, x => x.sharedMaterials);
            var replacements = new Dictionary<Material, Material>();
            string generated = null; GameObject marker = null;
            try
            {
                EnsureFolder(Root + "/Generated");
                generated = AssetDatabase.GenerateUniqueAssetPath(Root + "/Generated/Materials");
                AssetDatabase.CreateFolder(Root + "/Generated", Path.GetFileName(generated));
                Require(AssetDatabase.IsValidFolder(generated), "Could not create overlay-owned material directory.");
                foreach (var row in plan.materials)
                {
                    var clone = new Material(originals[row.name]) { name = row.name };
                    foreach (var slot in row.slots) clone.SetTexture(slot.property, AssetDatabase.LoadAssetAtPath<Texture2D>(slot.replacementPath));
                    if (row.calibrateParallax) clone.SetFloat("_Parallax", row.replacementParallax);
                    ValidatePair(originals[row.name], clone, row);
                    AssetDatabase.CreateAsset(clone, generated + "/" + row.name + ".mat");
                    replacements.Add(originals[row.name], clone);
                }
                foreach (var renderer in renderers)
                {
                    var changed = renderer.sharedMaterials;
                    for (int i = 0; i < changed.Length; i++) if (changed[i] != null && replacements.ContainsKey(changed[i])) changed[i] = replacements[changed[i]];
                    renderer.sharedMaterials = changed;
                }
                var receipt = new Receipt { schema = 1, planSha256 = ApprovedPlanSha256, baselineManifestSha256 = CoreManifestSha256,
                    sceneGuid = AssetDatabase.AssetPathToGUID(scene.path), names = plan.materials.Select(x => x.name).ToArray(),
                    originalPaths = plan.materials.Select(x => AssetPath(originals[x.name])).ToArray(),
                    clonePaths = plan.materials.Select(x => AssetPath(replacements[originals[x.name]])).ToArray(), unityRuntimeVerified = false };
                string receiptPath = generated + "/INSTALLATION.json";
                File.WriteAllText(receiptPath, JsonUtility.ToJson(receipt, true));
                AssetDatabase.ImportAsset(receiptPath, ImportAssetOptions.ForceSynchronousImport);
                string receiptGuid = AssetDatabase.AssetPathToGUID(receiptPath);
                Require(!string.IsNullOrEmpty(receiptGuid), "Installation receipt was not imported.");
                marker = new GameObject(Marker); SceneManager.MoveGameObjectToScene(marker, scene);
                new GameObject("Receipt_" + receiptGuid).transform.SetParent(marker.transform, false);
                ValidateExisting(plan, scene, core, marker);
                AssetDatabase.SaveAssets(); EditorSceneManager.MarkSceneDirty(scene);
                Debug.Log("Original PBR installed: 31 cloned definitions (30 active), 4 original families. Baseline assets and geometry preserved. Bake/runtime still unverified.");
            }
            catch
            {
                foreach (var pair in saved) if (pair.Key != null) pair.Key.sharedMaterials = pair.Value;
                if (marker != null) UnityEngine.Object.DestroyImmediate(marker);
                if (generated != null && AssetDatabase.IsValidFolder(generated)) AssetDatabase.DeleteAsset(generated);
                throw;
            }
        }

        static void ValidatePair(Material original, Material clone, MaterialRow row)
        {
            Require(original != null && clone != null && original.shader == clone.shader && original.name == clone.name, "Material identity/shader changed: " + row.name);
            Require(original.renderQueue == clone.renderQueue && original.enableInstancing == clone.enableInstancing
                && original.doubleSidedGI == clone.doubleSidedGI && original.globalIlluminationFlags == clone.globalIlluminationFlags
                && original.shaderKeywords.OrderBy(x => x).SequenceEqual(clone.shaderKeywords.OrderBy(x => x)), "Material rendering state changed: " + row.name);
            for (int i = 0; i < ShaderUtil.GetPropertyCount(original.shader); i++)
            {
                string property = ShaderUtil.GetPropertyName(original.shader, i);
                var type = ShaderUtil.GetPropertyType(original.shader, i);
                var slot = row.slots.SingleOrDefault(x => x.property == property);
                if (type == ShaderUtil.ShaderPropertyType.TexEnv)
                {
                    Require(original.GetTextureScale(property) == clone.GetTextureScale(property) && original.GetTextureOffset(property) == clone.GetTextureOffset(property), "Texture transform changed: " + row.name + " " + property);
                    if (slot != null) Require(AssetPath(original.GetTexture(property)) == slot.originalPath, "Historical source texture binding changed: " + row.name + " " + property);
                    string expected = slot == null ? AssetPath(original.GetTexture(property)) : slot.replacementPath;
                    Require(AssetPath(clone.GetTexture(property)) == expected, "Texture substitution differs: " + row.name + " " + property);
                }
                else if (type == ShaderUtil.ShaderPropertyType.Color) Require(original.GetColor(property) == clone.GetColor(property), "Tint changed: " + row.name);
                else if (type == ShaderUtil.ShaderPropertyType.Vector) Require(original.GetVector(property) == clone.GetVector(property), "Vector changed: " + row.name);
                else if (type == ShaderUtil.ShaderPropertyType.Float || type == ShaderUtil.ShaderPropertyType.Range)
                {
                    if (property == "_Parallax" && row.calibrateParallax) Require(Mathf.Approximately(original.GetFloat(property), row.originalParallax), "Historical parallax changed: " + row.name);
                    float expected = property == "_Parallax" && row.calibrateParallax ? row.replacementParallax : original.GetFloat(property);
                    Require(Mathf.Approximately(clone.GetFloat(property), expected), "Numeric material field changed: " + row.name + " " + property);
                }
                else throw new InvalidOperationException("Unreviewed shader property type: " + type);
            }
        }

        static void ValidateExisting(Plan plan, Scene scene, GameObject core, GameObject marker)
        {
            Require(marker.transform.childCount == 1 && marker.transform.GetChild(0).name.StartsWith("Receipt_", StringComparison.Ordinal), "Partial/foreign original PBR marker.");
            string receiptPath = AssetDatabase.GUIDToAssetPath(marker.transform.GetChild(0).name.Substring("Receipt_".Length));
            Require(Under(receiptPath, Root + "/Generated/") && receiptPath.EndsWith("/INSTALLATION.json", StringComparison.Ordinal), "Foreign original PBR receipt.");
            var receipt = JsonUtility.FromJson<Receipt>(File.ReadAllText(receiptPath));
            Require(receipt != null && receipt.schema == 1 && receipt.planSha256 == ApprovedPlanSha256
                && receipt.baselineManifestSha256 == CoreManifestSha256 && receipt.sceneGuid == AssetDatabase.AssetPathToGUID(scene.path), "Original PBR receipt belongs to another plan/scene.");
            Require(receipt.names != null && receipt.names.SequenceEqual(plan.materials.Select(x => x.name))
                && receipt.originalPaths != null && receipt.originalPaths.Length == 31 && receipt.clonePaths != null && receipt.clonePaths.Length == 31,
                "Incomplete original PBR receipt.");
            var renderers = core.GetComponentsInChildren<Renderer>(true);
            for (int i = 0; i < plan.materials.Length; i++)
            {
                var row = plan.materials[i];
                Require(Under(receipt.originalPaths[i], OriginalPrefix) && Under(receipt.clonePaths[i], Path.GetDirectoryName(receiptPath).Replace('\\', '/') + "/"), "Unowned receipt material path.");
                var original = AssetDatabase.LoadAssetAtPath<Material>(receipt.originalPaths[i]);
                var clone = AssetDatabase.LoadAssetAtPath<Material>(receipt.clonePaths[i]);
                ValidatePair(original, clone, row);
                var references = renderers.SelectMany(x => x.sharedMaterials).Where(x => x != null && x.name == row.name).ToArray();
                Require(references.Length == row.expectedRendererCount && references.All(x => x == clone), "Incomplete/changed renderer binding: " + row.name);
            }
            // No remaining scan-family map is allowed in an active core renderer.
            foreach (var material in renderers.SelectMany(x => x.sharedMaterials).Where(x => x != null).Distinct())
                foreach (var property in new[] { "_MainTex", "_BumpMap", "_ARM", "_HeightMap" })
                    if (material.HasProperty(property)) Require(!Under(AssetPath(material.GetTexture(property)), "Assets/TreeTopYokocho/Textures/PBR/"), "Active renderer still uses a historical scan texture: " + material.name);
        }

        [MenuItem("Tools/TreeTop Yokocho/0a - Audit Integrated Original PBR", false, 1)]
        public static void Audit()
        {
            Preflight(); var scene = SceneManager.GetActiveScene(); var core = Core(scene);
            var markers = scene.GetRootGameObjects().Where(x => x.name == Marker).ToArray();
            Require(markers.Length == 1, "Original PBR overlay is not installed exactly once.");
            ValidateExisting(LoadPlan(), scene, core, markers[0]);
            Debug.Log("Original PBR scene structure audit passed. Shader, UV scale, tint, non-target properties and 30 active material replacements and the unused Moss definition checked. Not a Unity bake/runtime/performance result.");
        }
    }
}
#endif

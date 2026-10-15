#if UNITY_EDITOR && !COMPILER_UDONSHARP
using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UdonSharp;
using UdonSharpEditor;

namespace TreeTopYokocho.EntrySystems.Editor
{
    // Additive installer. Never invokes the core world builder or edits its assets.
    public static class EntrySystemsInstaller
    {
        public const string Version = "0.1.0";
        public const string RootName = "EntrySystems_v1";
        public const string AssetRoot = "Assets/TreeTopYokochoEntrySystems";
        public const string SupportedManifestSha256 = "aa513b1c948ba9353a08c3d9eea6f4852f5d8ffa05715f036ea27d19f003d466";
        static readonly string[] Events = { "_PreviousHour", "_NextHour", "_SetAuto", "_CycleSpeed", "_ToggleMusic", "_NextTrack" };
        static readonly string[] Labels = { "時刻を1時間戻す（全体）", "時刻を1時間進める（全体）", "JST自動時刻（全体）", "時間の速度を切り替える（全体）", "BGM入・切（自分のみ）", "次の曲（自分のみ）" };

        [MenuItem("Tools/TreeTop Yokocho/8 - Install Entry Systems (Add-on)")]
        public static void Install()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
                throw new InvalidOperationException("Exit Play mode before installing entry systems.");
            Scene scene = SceneManager.GetActiveScene();
            if (!scene.IsValid() || !scene.isLoaded || string.IsNullOrEmpty(scene.path))
                throw new InvalidOperationException("Open and save the generated core world scene first.");
            string manifestPath = "Assets/TreeTopYokocho/Data/WorldManifest.json";
            if (!File.Exists(manifestPath) || Sha256(File.ReadAllBytes(manifestPath)) != SupportedManifestSha256)
                throw new InvalidOperationException("This addon supports the exact released v2.19 source manifest only.");
            ValidateCoreFiles();
            GameObject[] roots = scene.GetRootGameObjects();
            GameObject[] worlds = roots.Where(x => x.name == "TreeTopYokocho_v2").ToArray();
            if (worlds.Length != 1)
                throw new InvalidOperationException("Expected exactly one generated TreeTopYokocho_v2 scene root.");
            Transform core = worlds[0].transform;
            if (core.position != Vector3.zero || core.rotation != Quaternion.identity || core.localScale != Vector3.one)
                throw new InvalidOperationException("Core world transform was changed; certified entry positions no longer apply.");
            EntryPlazaBuilder.Preflight();
            GameObject[] installed = roots.Where(x => x.name == RootName).ToArray();
            if (installed.Length > 1) throw new InvalidOperationException("Duplicate addon roots; resolve manually before installation.");
            if (installed.Length == 1)
            {
                ValidateExisting(installed[0]);
                Debug.Log("Entry systems " + Version + " are already installed. No scene or asset changes were made.");
                return;
            }
            // Every asset/type/configuration check precedes scene or generated-asset writes.
            Material oldSky = RenderSettings.skybox;
            ValidateSky(oldSky);
            Light key = core.GetComponentsInChildren<Light>(true).SingleOrDefault(x => x.name == "BlueHour_Key");
            if (key == null || key.type != LightType.Directional)
                throw new InvalidOperationException("The generated BlueHour_Key directional light is missing or ambiguous.");
            if (core.GetComponentsInChildren<YokochoSafety>(true).Length != 1)
                throw new InvalidOperationException("The generated local fall-recovery component is missing or ambiguous.");
            Shader labelShader = Shader.Find("Unlit/Texture");
            Texture2D labels = AssetDatabase.LoadAssetAtPath<Texture2D>(AssetRoot + "/Textures/entry_control_labels.png");
            if (labelShader == null || labels == null)
                throw new InvalidOperationException("Entry control label shader or baked atlas has not imported.");
            Font statusFont = AssetDatabase.LoadAssetAtPath<Font>(AssetRoot + "/Fonts/YokochoEntryStatus.ttf");
            Shader statusShader = Shader.Find("TreeTopYokochoEntrySystems/DepthTestedStatusText");
            if (statusFont == null || statusFont.dynamic || statusFont.material == null || statusFont.material.mainTexture == null || statusShader == null)
                throw new InvalidOperationException("Reimport the addon ASCII status font and shader before installation.");
            AudioClip[] playlist = LoadPlaylist();

            GameObject root = null;
            string generated = null;
            try
            {
                EnsureFolder(AssetRoot + "/Generated");
                generated = AssetDatabase.GenerateUniqueAssetPath(AssetRoot + "/Generated/EntrySystems");
                AssetDatabase.CreateFolder(AssetRoot + "/Generated", Path.GetFileName(generated));
                if (!AssetDatabase.IsValidFolder(generated)) throw new IOException("Could not create addon-owned generated directory.");
                var sky = new Material(oldSky) { name = "EntrySystems_SkyClone" };
                AssetDatabase.CreateAsset(sky, generated + "/Sky.mat");
                var labelMaterial = new Material(labelShader) { name = "EntrySystems_ControlLabels", mainTexture = labels };
                AssetDatabase.CreateAsset(labelMaterial, generated + "/ControlLabels.mat");
                var statusMaterial = new Material(statusShader) { name = "EntrySystems_StatusText", mainTexture = statusFont.material.mainTexture };
                AssetDatabase.CreateAsset(statusMaterial, generated + "/StatusText.mat");
                root = new GameObject(RootName);
                SceneManager.MoveGameObjectToScene(root, scene);
                EntryPlazaBuilder.Build(root.transform, generated);
                Child(root.transform, "InstallationReceipt_" + EntryPlazaBuilder.ConfigDigest);
                Transform controls = new GameObject("SystemsControls").transform;
                controls.SetParent(root.transform, false);
                var clock = Child(root.transform, "GlobalClock").AddUdonSharpComponent<YokochoGlobalClock>();
                clock.installationVersion = Version;
                clock.installedCoreManifestSha256 = SupportedManifestSha256;
                clock.sun = key;
                clock.fillLight = null; // Baked fill cannot provide a dynamic-lighting promise.
                clock.skyMaterial = sky;
                clock.initialHour = 18.5f;
                clock.startInAuto = false;
                clock.statusText = Status(controls, "ClockStatus", new Vector3(-8f, 135.78f, -31.575f), .012f, statusFont, statusMaterial);
                var bgm = Child(root.transform, "LocalBGM").AddUdonSharpComponent<YokochoBgmController>();
                var audio = bgm.gameObject.AddComponent<AudioSource>();
                audio.playOnAwake = false; audio.loop = false; audio.spatialBlend = 0; audio.volume = .22f;
                bgm.musicSource = audio; bgm.playlist = playlist; bgm.defaultOn = false; bgm.volume = .22f;
                bgm.statusText = Status(controls, "MusicStatus", new Vector3(-8f, 135.65f, -31.575f), .008f, statusFont, statusMaterial);
                for (int i = 0; i < Events.Length; i++)
                    CreateButton(controls, i, i < 4 ? (UdonSharpBehaviour)clock : bgm, labelMaterial, generated);
                clock.ApplyProxyModifications(); bgm.ApplyProxyModifications();
                RenderSettings.skybox = sky;
                File.WriteAllText(generated + "/INSTALLATION.json", JsonUtility.ToJson(new Receipt {
                    addonVersion = Version, coreManifestSha256 = SupportedManifestSha256,
                    sceneAssetGuid = AssetDatabase.AssetPathToGUID(scene.path), originalSkyAssetPath = AssetDatabase.GetAssetPath(oldSky),
                    playlistCount = playlist.Length, unityRuntimeVerified = false
                }, true));
                AssetDatabase.ImportAsset(generated + "/INSTALLATION.json");
                ValidateExisting(root);
                AssetDatabase.SaveAssets();
                EditorSceneManager.MarkSceneDirty(scene); // User chooses whether/where to save.
                Selection.activeGameObject = root;
                Debug.Log("Entry systems installed. Save the scene, then compile Udon and perform the documented runtime/network tests. Music clips: " + playlist.Length);
                if (playlist.Length == 0) Debug.LogWarning("No MP3 clips supplied. BGM remains OFF/silent; add licensed MP3s and use the playlist refresh menu.");
            }
            catch
            {
                RenderSettings.skybox = oldSky;
                if (root != null) UnityEngine.Object.DestroyImmediate(root);
                if (generated != null && AssetDatabase.IsValidFolder(generated)) AssetDatabase.DeleteAsset(generated);
                throw;
            }
        }

        [MenuItem("Tools/TreeTop Yokocho/8a - Refresh Local MP3 Playlist")]
        public static void RefreshPlaylist()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Exit Play mode first.");
            var scene = SceneManager.GetActiveScene();
            var roots = scene.GetRootGameObjects().Where(x => x.name == RootName).ToArray();
            if (roots.Length != 1) throw new InvalidOperationException("Install the entry systems in this scene first.");
            ValidateExisting(roots[0]);
            var bgm = roots[0].GetComponentInChildren<YokochoBgmController>(true);
            AudioClip[] clips = LoadPlaylist();
            Undo.RecordObject(bgm, "Refresh local music playlist");
            bgm.playlist = clips; bgm.ApplyProxyModifications();
            EditorSceneManager.MarkSceneDirty(scene);
            Debug.Log("Local MP3 playlist refreshed: " + clips.Length + " clips. Default playback remains OFF.");
        }

        [MenuItem("Tools/TreeTop Yokocho/8b - Audit Installed Entry Systems")]
        public static void AuditInstalled()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Run this scene-structure audit outside Play mode; runtime checks are separate.");
            Scene scene = SceneManager.GetActiveScene();
            var roots = scene.GetRootGameObjects().Where(x => x.name == RootName).ToArray();
            if (roots.Length != 1) throw new InvalidOperationException("Expected one installed addon root.");
            ValidateCoreFiles(); EntryPlazaBuilder.Preflight(); ValidateExisting(roots[0]);
            var core = scene.GetRootGameObjects().Single(x => x.name == "TreeTopYokocho_v2");
            var safety = core.GetComponentInChildren<YokochoSafety>(true);
            if (safety == null || safety.walkableFloors == null) throw new InvalidOperationException("Core recovery floor roster missing.");
            Physics.SyncTransforms();
            var report = new System.Text.StringBuilder();
            report.AppendLine("Entry systems scene audit " + Version);
            report.AppendLine("Scope: installed bindings and assumed 0.325 m radius / 2.2 m headroom. Not Udon, multiplayer, avatar IK, visual-only geometry, bake or performance validation.");
            int failures = 0;
            var clock = roots[0].GetComponentInChildren<YokochoGlobalClock>(true);
            var music = roots[0].GetComponentInChildren<YokochoBgmController>(true);
            failures += AuditStatusLayout(report, clock.statusText, "TIME GLOBAL 23:59\nAUTO JST x1", 135.70f, 135.85f);
            failures += AuditStatusLayout(report, music.statusText, "BGM LOCAL / AUDIO ERROR\nOFF > ON TO RETRY", 135.61f, 135.70f);
            var config = EntryPlazaBuilder.LoadConfig();
            foreach (var warp in config.warps)
                failures += AuditStanding(report, warp.id + " destination", EntryPlazaBuilder.SourceToUnity(warp.destination), safety.walkableFloors);
            failures += AuditStanding(report, "Controls approach", EntryPlazaBuilder.SourceToUnity(config.systemsControlAnchor.standing), safety.walkableFloors);
            var manifest = JsonUtility.FromJson<global::TreeTopYokocho.Editor.Manifest>(File.ReadAllText("Assets/TreeTopYokocho/Data/WorldManifest.json"));
            for (int i = 0; i < manifest.spawns.Length; i++)
                failures += AuditStanding(report, "Core spawn " + i, EntryPlazaBuilder.SourceToUnity(manifest.spawns[i].position), safety.walkableFloors);
            int triangles = roots[0].GetComponentsInChildren<MeshFilter>(true).Where(x => x.sharedMesh != null).Sum(x => x.sharedMesh.triangles.Length / 3);
            report.AppendLine("Addon source scene mesh triangles: " + triangles);
            report.AppendLine("Addon MeshRenderers: " + roots[0].GetComponentsInChildren<MeshRenderer>(true).Length + " (not measured draw calls)");
            report.AppendLine("Addon MP3 clips: " + roots[0].GetComponentInChildren<YokochoBgmController>(true).playlist.Length);
            report.AppendLine("Failures: " + failures);
            report.AppendLine("Runtime acceptance still requires the separate MCP checklist.");
            string path = AssetRoot + "/Generated/EntrySystemsAudit.txt";
            File.WriteAllText(path, report.ToString()); AssetDatabase.ImportAsset(path);
            if (failures != 0) throw new InvalidOperationException("Entry scene audit failed. Read " + path);
            Debug.Log("Entry scene structure/collider audit passed. " + path + " Runtime checks remain required.");
        }
        static int AuditStatusLayout(System.Text.StringBuilder report, TextMesh text, string sample, float low, float high)
        {
            string original = text.text;
            try
            {
                var renderer = text.GetComponent<MeshRenderer>();
                text.text = "I";
                float narrow = renderer.bounds.size.x;
                text.text = "MMMMMMMMMMMMMMMMMMMM";
                float wide = renderer.bounds.size.x;
                if (narrow <= 0f || wide <= narrow * 1.5f)
                { report.AppendLine("FAIL " + text.name + ": text bounds did not visibly refresh between known strings. Inspect after an Editor render update; layout is not certified."); return 1; }
                text.text = sample;
                Bounds b = renderer.bounds;
                if (b.size.x <= .01f || b.size.y <= .01f || b.min.x < -8.70f || b.max.x > -7.30f || b.min.y < low || b.max.y > high || b.min.z < -31.63f || b.max.z > -31.55f)
                { report.AppendLine("FAIL " + text.name + ": dynamic status sample bounds unavailable, outside reserved text area, or overlapping controls."); return 1; }
                report.AppendLine("PASS " + text.name + ": representative two-line/time or empty-music label bounds."); return 0;
            }
            finally { text.text = original; }
        }

        static int AuditStanding(System.Text.StringBuilder report, string label, Vector3 point, Collider[] floors)
        {
            const float radius = .325f;
            float highest = float.NegativeInfinity, lowest = float.PositiveInfinity;
            for (int i = 0; i < 17; i++)
            {
                float angle = (i - 1) * Mathf.PI * 2f / 16f;
                Vector3 offset = i == 0 ? Vector3.zero : new Vector3(Mathf.Cos(angle) * radius, 0, Mathf.Sin(angle) * radius);
                RaycastHit hit;
                if (!Physics.Raycast(point + offset + Vector3.up * .5f, Vector3.down, out hit, 1f, ~0, QueryTriggerInteraction.Ignore) || !floors.Contains(hit.collider))
                { report.AppendLine("FAIL " + label + ": footprint lacks an authenticated walkable-floor hit."); return 1; }
                highest = Mathf.Max(highest, hit.point.y); lowest = Mathf.Min(lowest, hit.point.y);
            }
            if (highest - lowest > .08f)
            { report.AppendLine("FAIL " + label + ": footprint is not near-flat."); return 1; }
            Vector3 bottom = new Vector3(point.x, highest + .06f + radius, point.z);
            Vector3 top = new Vector3(point.x, highest + 2.2f - radius, point.z);
            Collider[] contacts = Physics.OverlapCapsule(bottom, top, radius, ~0, QueryTriggerInteraction.Ignore);
            if (contacts.Length != 0)
            { report.AppendLine("FAIL " + label + ": body collider contact: " + string.Join(", ", contacts.Select(x => x.name).ToArray())); return 1; }
            report.AppendLine("PASS " + label + ": floor footprint and body collider envelope."); return 0;
        }

        static void ValidateExisting(GameObject root)
        {
            if (root.transform.position != Vector3.zero || root.transform.rotation != Quaternion.identity || root.transform.localScale != Vector3.one)
                throw new InvalidOperationException("Addon transform changed; certified placement is no longer preserved.");
            if (root.transform.Find("InstallationReceipt_" + EntryPlazaBuilder.ConfigDigest) == null)
                throw new InvalidOperationException("Addon configuration receipt is absent or differs. No overwrite is allowed.");
            var clocks = root.GetComponentsInChildren<YokochoGlobalClock>(true);
            var music = root.GetComponentsInChildren<YokochoBgmController>(true);
            var buttons = root.GetComponentsInChildren<YokochoEntryControl>(true);
            if (clocks.Length != 1 || music.Length != 1 || buttons.Length != Events.Length || root.transform.Find("EntryPlaza") == null || root.transform.Find("SystemsControls") == null)
                throw new InvalidOperationException("An incomplete or foreign EntrySystems_v1 exists. No automatic overwrite is allowed.");
            var clock = clocks[0];
            if (clock.installationVersion != Version || clock.installedCoreManifestSha256 != SupportedManifestSha256 || clock.skyMaterial == null || clock.sun == null || clock.statusText == null || music[0].statusText == null || music[0].musicSource == null)
                throw new InvalidOperationException("Existing addon version, supported core, or component references differ. Preserve your scene and repair explicitly.");
            if (!AssetDatabase.GetAssetPath(clock.skyMaterial).StartsWith(AssetRoot + "/Generated/", StringComparison.Ordinal))
                throw new InvalidOperationException("Addon sky is not an owned clone.");
            var core = root.scene.GetRootGameObjects().Single(x => x.name == "TreeTopYokocho_v2");
            if (core.transform.position != Vector3.zero || core.transform.rotation != Quaternion.identity || core.transform.localScale != Vector3.one)
                throw new InvalidOperationException("Core transform no longer matches audited source coordinates.");
            var recovery = core.GetComponentsInChildren<YokochoSafety>(true).Single();
            if (clock.sun != core.GetComponentsInChildren<Light>(true).Single(x => x.name == "BlueHour_Key") || RenderSettings.skybox != clock.skyMaterial)
                throw new InvalidOperationException("Clock sky/key references differ from the owned installation.");
            var warps = root.GetComponentsInChildren<YokochoTeleport>(true);
            var spec = EntryPlazaBuilder.LoadConfig();
            if (warps.Length != spec.warps.Length) throw new InvalidOperationException("Addon warp roster differs.");
            foreach (var expected in spec.warps)
            {
                var matches = warps.Where(x => x.name == expected.id).ToArray();
                if (matches.Length != 1 || matches[0].destination == null || matches[0].recovery != recovery || !matches[0].destination.IsChildOf(root.transform) ||
                    Quaternion.Angle(matches[0].destination.rotation, Quaternion.LookRotation(EntryPlazaBuilder.SourceToUnity(expected.forward))) > .001f ||
                    matches[0].transform.rotation != Quaternion.identity || matches[0].transform.lossyScale != Vector3.one ||
                    Vector3.Distance(matches[0].destination.position, EntryPlazaBuilder.SourceToUnity(expected.destination)) > .0001f ||
                    Vector3.Distance(matches[0].transform.position, EntryPlazaBuilder.SourceToUnity(expected.position)) > .0001f)
                    throw new InvalidOperationException("Addon warp destination/recovery/placement differs.");
                var box = matches[0].GetComponent<BoxCollider>();
                if (box == null || !box.isTrigger || box.center != Vector3.zero || Vector3.Distance(box.size, EntryPlazaBuilder.SourceToUnity(expected.size)) > .0001f || matches[0].gameObject.layer != 8)
                    throw new InvalidOperationException("Addon warp interaction collider differs.");
            }
            for (int i = 0; i < Events.Length; i++)
            {
                string evt = Events[i];
                var matches = buttons.Where(x => x.eventName == evt && x.target == (i < 4 ? (UdonSharpBehaviour)clock : music[0])).ToArray();
                Vector3 position = ButtonPosition(i);
                if (matches.Length != 1 || Vector3.Distance(matches[0].transform.position, position) > .0001f || matches[0].transform.rotation != Quaternion.identity || matches[0].transform.lossyScale != Vector3.one)
                    throw new InvalidOperationException("Existing addon control binding or transform differs; refusing silent replacement.");
                var box = matches[0].GetComponent<BoxCollider>();
                if (box == null || !box.isTrigger || box.center != Vector3.zero || Vector3.Distance(box.size, new Vector3(.60f, .19f, .035f)) > .0001f || matches[0].gameObject.layer != 8)
                    throw new InvalidOperationException("Existing addon control collider differs.");
            }
        }

        static void ValidateCoreFiles()
        {
            string path = AssetRoot + "/Data/CoreCompatibility.json";
            if (!File.Exists(path) || Sha256(File.ReadAllBytes(path)) != "beb8445ca4efb4529d5fc5f9a89832e8fcc53128e205dae5a0befd91567d497a") throw new InvalidOperationException("Missing or changed addon compatibility manifest.");
            var manifest = JsonUtility.FromJson<CoreCompatibility>(File.ReadAllText(path));
            if (manifest == null || manifest.version != "2.19.0" || manifest.files == null || manifest.files.Length != 13)
                throw new InvalidOperationException("Invalid addon compatibility manifest.");
            foreach (var file in manifest.files)
                if (file == null || string.IsNullOrEmpty(file.path) || !file.path.StartsWith("Assets/TreeTopYokocho/", StringComparison.Ordinal) || file.path.Contains("..") || !File.Exists(file.path) || Sha256(File.ReadAllBytes(file.path)) != file.sha256)
                    throw new InvalidOperationException("Core source/geometry differs from supported v2.19. Restore or use a separately reviewed addon revision.");
            string compressed = "Assets/TreeTopYokocho/Data/VisualMeshes.bytes.gz";
            if (File.Exists(compressed) && Sha256(File.ReadAllBytes(compressed)) != "c5d324af8e0e5ea2ad1ddfb22fa050d24b7652cbe22d26079eb7265b807dee29")
                throw new InvalidOperationException("A stale combined visual gzip overrides the verified shards. Remove the stale authoring artifact before rebuilding.");
        }
        [Serializable] class CoreCompatibility { public string version; public CoreFile[] files; }
        [Serializable] class CoreFile { public string path, sha256; }

        static AudioClip[] LoadPlaylist()
        {
            string music = AssetRoot + "/Music";
            if (!AssetDatabase.IsValidFolder(music)) return new AudioClip[0];
            return AssetDatabase.FindAssets("t:AudioClip", new[] { music }).Select(AssetDatabase.GUIDToAssetPath)
                .Where(x => string.Equals(Path.GetExtension(x), ".mp3", StringComparison.OrdinalIgnoreCase))
                .OrderBy(x => x, StringComparer.Ordinal).Select(x => {
                    var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(x);
                    if (clip == null || clip.length <= 0) throw new InvalidOperationException("MP3 import is incomplete: " + x);
                    return clip;
                }).ToArray();
        }
        static void ValidateSky(Material sky)
        {
            string[] props = { "_Zenith", "_Horizon", "_SkyStrength", "_SunsetColor", "_SunsetDirection", "_StarStrength", "_AuroraStrength", "_HighCloudTint" };
            if (sky == null || sky.shader == null || sky.shader.name != "TreeTopYokocho/BlueHourSky" || props.Any(x => !sky.HasProperty(x)))
                throw new InvalidOperationException("The supported core sky material is missing or incompatible.");
        }
        static GameObject Child(Transform parent, string name) { var go = new GameObject(name); go.transform.SetParent(parent, false); return go; }
        static TextMesh Status(Transform parent, string name, Vector3 position, float size, Font font, Material material)
        {
            var text = Child(parent, name).AddComponent<TextMesh>();
            text.transform.position = position; text.transform.rotation = Quaternion.Euler(0, 180, 0);
            text.text = name == "ClockStatus" ? "GLOBAL 18:30  MANUAL" : "LOCAL MUSIC: OFF";
            text.font = font; text.GetComponent<MeshRenderer>().sharedMaterial = material;
            text.fontSize = 48; text.characterSize = size; text.anchor = TextAnchor.MiddleCenter;
            text.alignment = TextAlignment.Center; text.color = new Color(.10f, .16f, .13f); // Dark ink on the cream panel, not pale ink on pale paper.
            return text;
        }
        static Vector3 ButtonPosition(int index)
        {
            return new Vector3(-8f + (index % 2 == 0 ? .36f : -.36f), 135.50f - (index / 2) * .24f, -31.59f);
        }
        static void CreateButton(Transform parent, int index, UdonSharpBehaviour target, Material material, string generated)
        {
            var go = Child(parent, "Control_" + index); go.layer = 8;
            go.transform.position = ButtonPosition(index);
            var collider = go.AddComponent<BoxCollider>(); collider.size = new Vector3(.60f, .19f, .035f); collider.isTrigger = true;
            var mesh = new Mesh { name = "ControlLabel_" + index };
            // Face +Z (source +Y); atlas has one horizontal strip per control.
            mesh.vertices = new[] { new Vector3(-.30f,-.095f,.019f), new Vector3(.30f,-.095f,.019f), new Vector3(.30f,.095f,.019f), new Vector3(-.30f,.095f,.019f) };
            float low = 1f - (index + 1) / 6f, high = 1f - index / 6f;
            mesh.uv = new[] { new Vector2(1,low), new Vector2(0,low), new Vector2(0,high), new Vector2(1,high) };
            mesh.triangles = new[] { 0, 1, 2, 0, 2, 3 }; mesh.RecalculateNormals(); mesh.RecalculateBounds();
            AssetDatabase.CreateAsset(mesh, generated + "/ControlLabel_" + index + ".asset");
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            go.AddComponent<MeshRenderer>().sharedMaterial = material;
            var control = go.AddUdonSharpComponent<YokochoEntryControl>();
            control.target = target; control.eventName = Events[index]; control.cooldownSeconds = .4f; control.ApplyProxyModifications();
            var backing = UdonSharpEditorUtility.GetBackingUdonBehaviour(control);
            if (backing == null) throw new InvalidOperationException("Udon backing behaviour was not created.");
            backing.interactText = Labels[index]; backing.proximity = 1.8f; EditorUtility.SetDirty(backing);
        }
        static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/'); EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }
        static string Sha256(byte[] bytes) { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant(); }
        [Serializable] class Receipt { public string addonVersion, coreManifestSha256, sceneAssetGuid, originalSkyAssetPath; public int playlistCount; public bool unityRuntimeVerified; }
    }
}
#endif

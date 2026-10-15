#if UNITY_EDITOR && !COMPILER_UDONSHARP
using System;
using System.IO;
using System.Globalization;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using TreeTopYokocho.EntrySystems.Editor;

namespace TreeTopYokocho.Integration.Editor
{
    // Package version is separate from the immutable v2.19 geometry baseline.
    public static class IntegratedPreviewBuilder
    {
        public const string PackageVersion = "2.20.0-preview.1";
        const string Menu = "Tools/TreeTop Yokocho/0 - Build or Complete Preview";

        [MenuItem(Menu, false, 0)]
        public static void BuildOrComplete()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode || EditorApplication.isCompiling || EditorApplication.isUpdating)
                throw new InvalidOperationException("Wait for import/compilation and exit Play mode before building.");
            // Verify reviewed source and all original maps before the core builder mutates anything.
            OriginalPbrInstaller.Preflight();
            PreflightEntrySources();
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            if (SceneManager.GetActiveScene().isDirty)
                throw new InvalidOperationException("The active scene still has unsaved edits. Save explicitly before completing it; choosing Do not Save must not cause those edits to be saved later.");
            var scene = SceneManager.GetActiveScene();
            var worlds = scene.GetRootGameObjects().Where(x => x.name == "TreeTopYokocho_v2").ToArray();
            if (worlds.Length > 1) throw new InvalidOperationException("Ambiguous core roots. Resolve manually; no scene was replaced.");
            if (worlds.Length == 0)
            {
                global::TreeTopYokocho.Editor.YokochoWorldBuilder.Build();
                scene = SceneManager.GetActiveScene();
                worlds = scene.GetRootGameObjects().Where(x => x.name == "TreeTopYokocho_v2").ToArray();
                if (worlds.Length == 0) return; // A cancelled core save dialog is not a successful build.
                if (worlds.Length != 1) throw new InvalidOperationException("Core generation did not leave exactly one world.");
            }
            AuditCoreBeforeChanges();
            PreflightEntryScene(scene, worlds[0]);
            // Both installers return without new objects/assets when the exact complete install exists.
            // A partial/foreign install fails closed. A later failure never deletes the preserved core.
            OriginalPbrInstaller.Install();
            EntrySystemsInstaller.Install();
            OriginalPbrInstaller.Audit();
            EntrySystemsInstaller.AuditInstalled();
            if (!EditorSceneManager.SaveScene(scene))
                throw new IOException("Could not save the integrated scene. Keep the editor open and save manually.");
            Debug.Log("Tree-top Yokocho " + PackageVersion + " source preview assembled and saved: " + scene.path
                + ". Includes original PBR, entry plaza/warps, global clock and local MP3 controls. "
                + "No upload, Udon runtime, multiplayer, audio, light bake or headset validation was performed by this menu.");
        }

        static void PreflightEntrySources()
        {
            EntryPlazaBuilder.Preflight();
            const string root = "Assets/TreeTopYokochoEntrySystems";
            var labels = AssetDatabase.LoadAssetAtPath<Texture2D>(root + "/Textures/entry_control_labels.png");
            var font = AssetDatabase.LoadAssetAtPath<Font>(root + "/Fonts/YokochoEntryStatus.ttf");
            if (labels == null || Shader.Find("Unlit/Texture") == null || font == null || font.dynamic
                || font.material == null || font.material.mainTexture == null
                || Shader.Find("TreeTopYokochoEntrySystems/DepthTestedStatusText") == null)
                throw new InvalidOperationException("Entry labels, static ASCII font or shaders have not imported. No material installation was started.");
        }

        static void AuditCoreBeforeChanges()
        {
            // The unchanged core audit uses GameObject.Find and logs instead of throwing on errors.
            // Isolate its target and read THIS invocation's timestamped report, never a stale PASS.
            if (SceneManager.sceneCount != 1)
                throw new InvalidOperationException("Use a single loaded world scene for the core physics audit.");
            DateTime started = DateTime.UtcNow;
            global::TreeTopYokocho.Editor.YokochoWorldBuilder.Audit();
            const string path = "Assets/TreeTopYokocho/Generated/PhysicsAudit.txt";
            var lines = File.ReadAllLines(path);
            string utc = lines.SingleOrDefault(x => x.StartsWith("UTC: ", StringComparison.Ordinal));
            DateTime written;
            if (utc == null || !DateTime.TryParse(utc.Substring(5), CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out written)
                || written.ToUniversalTime() < started || lines.Count(x => x == "Errors: 0") != 1)
                throw new InvalidOperationException("Current core physics audit did not report Errors: 0. Read PhysicsAudit.txt; integration stopped.");
        }

        static void PreflightEntryScene(Scene scene, GameObject core)
        {
            var t = core.transform;
            if (t.position != Vector3.zero || t.rotation != Quaternion.identity || t.localScale != Vector3.one)
                throw new InvalidOperationException("The core transform was changed.");
            var installed = scene.GetRootGameObjects().Where(x => x.name == EntrySystemsInstaller.RootName).ToArray();
            if (installed.Length > 1) throw new InvalidOperationException("Duplicate entry roots; resolve manually.");
            if (installed.Length == 1)
            {
                // Public scene validation authenticates all existing entry references and rejects a partial install.
                // It writes an audit report and temporarily measures status text, restoring it in finally.
                EntrySystemsInstaller.AuditInstalled();
                return;
            }
            var key = core.GetComponentsInChildren<Light>(true).Where(x => x.name == "BlueHour_Key").ToArray();
            if (key.Length != 1 || key[0].type != LightType.Directional || core.GetComponentsInChildren<YokochoSafety>(true).Length != 1)
                throw new InvalidOperationException("The core key light or safety component is missing or ambiguous.");
            var sky = RenderSettings.skybox;
            string[] properties = { "_Zenith", "_Horizon", "_SkyStrength", "_SunsetColor", "_SunsetDirection", "_StarStrength", "_AuroraStrength", "_HighCloudTint" };
            if (sky == null || sky.shader == null || sky.shader.name != "TreeTopYokocho/BlueHourSky" || properties.Any(x => !sky.HasProperty(x)))
                throw new InvalidOperationException("The supported core sky is missing or incompatible.");
        }
    }
}
#endif

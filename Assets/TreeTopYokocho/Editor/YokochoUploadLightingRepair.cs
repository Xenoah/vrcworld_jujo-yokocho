#if UNITY_EDITOR && !COMPILER_UDONSHARP
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace TreeTopYokocho.Editor
{
    // Explicit opt-in repair on a saved scene copy. Original generated meshes
    // remain untouched; no geometry, collision or interaction roster is removed.
    public static class YokochoUploadLightingRepair
    {
        static Queue<MeshRenderer> pending;
        static List<string> report;
        static string folder;
        static Transform anchors;
        static Vector3[] probes;
        static int unwrapped, probeLit;
        static string Report;

        [MenuItem("Tools/TreeTop Yokocho/9b - Repair Lightmap Detail Allocation")]
        public static void Prepare()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode || Lightmapping.isRunning || pending != null)
                throw new InvalidOperationException("Stop Play/baking and finish any existing repair first.");
            var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
            if (string.IsNullOrEmpty(scene.path) || !scene.path.StartsWith("Assets/", StringComparison.Ordinal))
                throw new InvalidOperationException("Save the scene inside Assets before repairing its lighting.");
            var root = GameObject.Find("TreeTopYokocho_v2");
            if (root == null || LightmapSettings.lightmaps.Length == 0 || LightmapSettings.lightProbes == null)
                throw new InvalidOperationException("A previously baked core is required for measured chart sizing.");
            if (root.transform.Find("SmallDetailProbeAnchors") != null)
                throw new InvalidOperationException("Lighting repair is already present. Re-bake and inspect its report; do not apply it twice.");
            string backup = AssetDatabase.GenerateUniqueAssetPath(Path.GetDirectoryName(scene.path).Replace('\\', '/')
                + "/" + scene.name + "_BeforeLightingRepair.unity");
            if (!EditorSceneManager.SaveScene(scene, backup, true))
                throw new IOException("Could not preserve a scene backup. No repair was started.");
            folder = AssetDatabase.GenerateUniqueAssetPath("Assets/TreeTopYokocho/Generated/LightingRepairMeshes");
            Directory.CreateDirectory(folder); AssetDatabase.Refresh();
            Directory.CreateDirectory("Logs");
            Report = "Logs/TreeTopYokochoLightingRepair-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + ".txt";
            var anchorGo = new GameObject("SmallDetailProbeAnchors");
            anchorGo.transform.SetParent(root.transform, false); anchors = anchorGo.transform;
            probes = LightmapSettings.lightProbes.positions;
            pending = new Queue<MeshRenderer>(root.GetComponentsInChildren<MeshRenderer>(true)
                .Where(r => r.lightmapIndex >= 0 && r.lightmapIndex < LightmapSettings.lightmaps.Length));
            report = new List<string> { "UTC " + DateTime.UtcNow.ToString("O"), "Scene backup " + backup, "Renderers " + pending.Count };
            unwrapped = probeLit = 0;
            EditorApplication.update += Step;
        }

        static void Step()
        {
            try
            {
                if (pending.Count == 0)
                {
                    EditorApplication.update -= Step; pending = null;
                    AssetDatabase.SaveAssets();
                    EditorSceneManager.MarkSceneDirty(anchors.gameObject.scene);
                    EditorSceneManager.SaveScene(anchors.gameObject.scene);
                    report.Add("COMPLETED unwrapped=" + unwrapped + " probeLit=" + probeLit);
                    File.WriteAllLines(Report, report);
                    return;
                }
                var r = pending.Dequeue();
                float span = Mathf.Min(r.lightmapScaleOffset.x, r.lightmapScaleOffset.y)
                    * LightmapSettings.lightmaps[r.lightmapIndex].lightmapColor.width;
                if (span < 32f || IsThinDetail(r.name))
                {
                    // A sub-32px atlas allocation cannot resolve the many tiny
                    // disconnected charts on nails, fittings and lamp details.
                    // Still contribute to baked occlusion, but receive probes.
                    r.receiveGI = ReceiveGI.LightProbes;
                    r.lightProbeUsage = LightProbeUsage.BlendProbes;
                    var a = new GameObject(r.name + "_ProbeAnchor").transform;
                    a.SetParent(anchors, false);
                    a.position = probes.OrderBy(p => (p - r.bounds.center).sqrMagnitude).First();
                    r.probeAnchor = a; // sample inside the probe volume, never extrapolate
                    probeLit++;
                    report.Add("PROBE " + r.name + " previousPixels=" + span);
                }
                else
                {
                    var filter = r.GetComponent<MeshFilter>();
                    var source = filter.sharedMesh;
                    var mesh = UnityEngine.Object.Instantiate(source);
                    mesh.name = source.name + "_LightmapRepair";
                    MeshUtility.SetMeshCompression(mesh, ModelImporterMeshCompression.Off);
                    UnwrapParam.SetDefaults(out var parameters);
                    // Original default was 4/1024 even for 32-250px allocations.
                    // Repack with a measured margin and increase receiver density.
                    parameters.packMargin = Mathf.Clamp(4f / (span * 2f), .0078125f, .0625f);
                    if (!Unwrapping.GenerateSecondaryUVSet(mesh, parameters))
                        throw new InvalidOperationException("UV2 generation failed: " + r.name);
                    if (mesh.triangles.Length != source.triangles.Length)
                        throw new InvalidOperationException("Unexpected topology change: " + r.name);
                    var beforeVertices = source.vertices; var beforeIndices = source.triangles;
                    var afterVertices = mesh.vertices; var afterIndices = mesh.triangles;
                    for (int i = 0; i < beforeIndices.Length; i++)
                        if ((beforeVertices[beforeIndices[i]] - afterVertices[afterIndices[i]]).sqrMagnitude > 1e-10f)
                            throw new InvalidOperationException("Unwrap changed triangle positions: " + r.name);
                    string path = folder + "/" + r.name + ".asset";
                    AssetDatabase.CreateAsset(mesh, path); filter.sharedMesh = mesh;
                    r.scaleInLightmap *= 2f;
                    unwrapped++;
                    report.Add("UV2 " + r.name + " previousPixels=" + span + " margin=" + parameters.packMargin);
                }
                EditorUtility.SetDirty(r);
                if (pending.Count % 25 == 0) File.WriteAllLines(Report, report.Concat(new[] { "PENDING " + pending.Count }));
            }
            catch (Exception exception)
            {
                EditorApplication.update -= Step; pending = null;
                report.Add("FAILED " + exception); File.WriteAllLines(Report, report);
                Debug.LogException(exception);
            }
        }

        static bool IsThinDetail(string name)
        {
            // These authored narrow overlays still had overlapping chart
            // neighbourhoods after repacking. Their structural parent meshes
            // remain lightmapped; only the decorative overlay receives probes.
            switch (name)
            {
                case "Mesh_Railings_L2_HandCraft_Cedar":
                case "Mesh_Railings_L2_HandCraft_DarkTimber":
                case "Mesh_Railings_L3_HandCraft_Cedar":
                case "Mesh_Railings_G0_HandCraft_Cedar":
                case "Mesh_Railings_L1_HandCraft_Cedar":
                case "Mesh_Railings_L3_HandCraft_DarkTimber":
                case "Mesh_Railings_G0_HandCraft_DarkTimber":
                case "Mesh_Railings_L1_HandCraft_DarkTimber":
                case "Mesh_Infrastructure_Lift_Feed_UtilityCable":
                case "Mesh_Decks_L2_Planks_DeckRepair":
                case "Mesh_Shops_S05_Personality_JoineryFinish_Food_Copper":
                    return true;
                default:
                    return false;
            }
        }
    }
}
#endif

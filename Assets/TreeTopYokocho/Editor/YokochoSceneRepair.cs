#if UNITY_EDITOR && !COMPILER_UDONSHARP
using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace TreeTopYokocho.Editor
{
    public static class YokochoSceneRepair
    {
        [MenuItem("Tools/TreeTop Yokocho/9 - Repair Distant Light Probes")]
        public static void RepairDistantLightProbes()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode || Lightmapping.isRunning)
                throw new InvalidOperationException("Exit Play mode and wait for baking before repair.");
            var root = GameObject.Find("TreeTopYokocho_v2");
            if (root == null) throw new InvalidOperationException("Open the generated world scene first.");
            int changed = 0;
            foreach (var renderer in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                if (!renderer.name.StartsWith("Mesh_Landscape_", StringComparison.Ordinal)
                    || renderer.lightProbeUsage == LightProbeUsage.Off) continue;
                Undo.RecordObject(renderer, "Repair distant scenery probe extrapolation");
                renderer.lightProbeUsage = LightProbeUsage.Off;
                EditorUtility.SetDirty(renderer);
                changed++;
            }
            if (changed != 0) EditorSceneManager.MarkSceneDirty(root.scene);
            Debug.Log("Distant lighting repair: " + changed + " renderers now use ambient lighting instead of local light probes. Save the scene to retain the fix.");
        }
    }
}
#endif

#if UNITY_EDITOR && !COMPILER_UDONSHARP
namespace TreeTopYokocho.Integration.Editor
{
    // An explicit local compatibility revision, not a replacement of the v2.19
    // pins. Geometry, manifest, map bytes and all other source pins stay exact.
    // Scope/evidence: Docs/LOCAL_REPAIR_REVISION_20261015_JA.md.
    internal static class LocalCoreRepairRevision
    {
        public static bool Matches(string path, string baselineHash, string currentHash)
        {
            if (currentHash == baselineHash) return true;
            switch (path)
            {
                case "Assets/TreeTopYokocho/Editor/YokochoWorldBuilder.cs":
                    return baselineHash == "754a1631251b18fed9ce264a53a41535289af908f3ef75bcf293beaec8555e15"
                        && currentHash == "e29ca78a19aac6fd49d494ee5e250b5b0875d4fb149040c58f26c3929780b4c2";
                case "Assets/TreeTopYokocho/Shaders/YokochoSky.shader":
                    return baselineHash == "34e9824ecf602aedeb37a4417c393b3f7f5825c9fd3e07b2298ebcbfcb173f91"
                        && currentHash == "da1989341178e2f6cb9162ec58e73122b48b1c916b6d5abc9a4fcd615392001b";
                default:
                    return false;
            }
        }
    }
}
#endif

#if UNITY_EDITOR && !COMPILER_UDONSHARP
using System;
using UnityEditor;
using UnityEngine;

namespace TreeTopYokocho.Integration.Editor
{
    public class OriginalPbrImporter : AssetPostprocessor
    {
        void OnPreprocessTexture()
        {
            const string prefix = "Assets/TreeTopYokochoOriginalPbr/Textures/PBR/";
            if (!assetPath.StartsWith(prefix, StringComparison.Ordinal)) return;
            if (!assetPath.EndsWith(".png", StringComparison.OrdinalIgnoreCase)) return;
            var importer = (TextureImporter)assetImporter;
            bool normal = assetPath.EndsWith("_normalGL.png", StringComparison.Ordinal);
            bool albedo = assetPath.EndsWith("_albedo.png", StringComparison.Ordinal);
            bool terrain = assetPath.IndexOf("/yokocho_mineral_rock_", StringComparison.Ordinal) >= 0;
            int cap = albedo && !terrain ? 2048 : 1024;
            importer.textureType = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
            importer.sRGBTexture = albedo;
            importer.flipGreenChannel = false; // Supplied tangent normals are OpenGL +Y.
            importer.convertToNormalmap = false; // Never synthesize normals from RGB luminance.
            importer.swizzleR = TextureImporterSwizzle.R; importer.swizzleG = TextureImporterSwizzle.G;
            importer.swizzleB = TextureImporterSwizzle.B; importer.swizzleA = TextureImporterSwizzle.A;
            importer.alphaSource = TextureImporterAlphaSource.None;
            importer.mipmapEnabled = true;
            importer.wrapMode = TextureWrapMode.Repeat;
            importer.filterMode = FilterMode.Trilinear;
            importer.anisoLevel = 4;
            importer.isReadable = false;
            importer.maxTextureSize = cap;
            importer.textureCompression = TextureImporterCompression.CompressedHQ;
            var platform = importer.GetPlatformTextureSettings("Standalone");
            platform.name = "Standalone";
            platform.overridden = true;
            platform.maxTextureSize = cap;
            platform.format = normal ? TextureImporterFormat.BC5 : TextureImporterFormat.BC7;
            platform.textureCompression = TextureImporterCompression.CompressedHQ;
            importer.SetPlatformTextureSettings(platform);
        }
    }
}
#endif

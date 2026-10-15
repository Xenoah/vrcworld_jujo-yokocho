#if UNITY_EDITOR && !COMPILER_UDONSHARP
using UnityEditor;
using UnityEngine;
namespace TreeTopYokocho.EntrySystems.Editor
{
    public sealed class EntryAssetImporter : AssetPostprocessor
    {
        void OnPreprocessAsset()
        {
            if (assetPath == EntrySystemsInstaller.AssetRoot + "/Fonts/YokochoEntryStatus.ttf")
            {
                var font = assetImporter as TrueTypeFontImporter;
                if (font == null) return;
                font.fontTextureCase = FontTextureCase.ASCII;
                font.fontSize = 48;
                font.includeFontData = true;
                font.fontNames = new string[0];
                font.fontReferences = new Font[0];
            }
        }
        void OnPreprocessTexture()
        {
            if (assetPath != EntrySystemsInstaller.AssetRoot + "/Textures/entry_control_labels.png") return;
            var texture = (TextureImporter)assetImporter;
            texture.textureType = TextureImporterType.Default;
            texture.sRGBTexture = true; texture.mipmapEnabled = true;
            texture.npotScale = TextureImporterNPOTScale.None;
            texture.wrapMode = TextureWrapMode.Clamp; texture.filterMode = FilterMode.Bilinear;
            texture.maxTextureSize = 2048; texture.textureCompression = TextureImporterCompression.CompressedHQ;
            texture.alphaSource = TextureImporterAlphaSource.None;
        }
    }
}
#endif

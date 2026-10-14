#if UNITY_EDITOR && !COMPILER_UDONSHARP
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Security.Cryptography;
using System.Collections.Generic;
using UnityEngine;

namespace TreeTopYokocho.Editor
{
    [Serializable] public sealed class VenueLightingLightSpec
    {
        public int schema;
        public string venueId, fixtureId, role;
        public float[] color;
        public float intensityMultiplier;
    }
    [Serializable] public sealed class VenueLightingFixture
    {
        public string id, role;
        public int manifestIndex;
        public float[] localPosition, worldPosition, color;
        public float range, strength, intensityMultiplier;
    }
    [Serializable] public sealed class VenueLightingEmitter
    {
        public string group, sourceMaterial, material, shader;
        public string[] fixtureIds;
        public float[] color;
        public float emission, paperRelief, breath;
    }
    [Serializable] public sealed class VenueLightingShop
    {
        public string id, theme;
        public VenueLightingFixture[] fixtures;
        public VenueLightingEmitter[] emitters;
    }
    [Serializable] public sealed class VenueLightingManifest
    {
        public int schema;
        public string profileVersion, profileSha256;
        public int[] ownedLightIndices;
        public VenueLightingEmitter[] emitterBindings;
    }

    // Editor-only, bounded, static material/light authoring. Never loaded by Udon.
    [Serializable] public sealed class VenueLightingProfile
    {
        public int schema;
        public string version, feature, colorSpace;
        public float[] legacyUnityColor, legacyPreviewColor;
        public float unityBaseIntensity, previewBaseEnergy, rangeMultiplier, bounceIntensity;
        public VenueLightingShop[] shops;
        static readonly int[] Counts = { 2, 2, 2, 1, 2, 2, 2, 2 };

        static void Require(bool condition, string label)
        {
            if (!condition) throw new InvalidDataException("Venue lighting: " + label);
        }
        static void Scalar(float value, float low, float high, string label)
        {
            Require(!float.IsNaN(value) && !float.IsInfinity(value) && value >= low && value <= high, label);
        }
        static void Vector(float[] value, float low, float high, string label)
        {
            Require(value != null && value.Length == 3, label);
            foreach (float component in value) Scalar(component, low, high, label);
        }
        static bool Same(float[] a, float[] b)
        {
            return a != null && b != null && a.Length == b.Length && a.SequenceEqual(b);
        }
        static float Luma(float[] rgb) { return .2126f*rgb[0] + .7152f*rgb[1] + .0722f*rgb[2]; }
        static Color RGB(float[] rgb) { return new Color(rgb[0], rgb[1], rgb[2]); }
        static string Digest(byte[] bytes)
        {
            using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
        }

        public static VenueLightingProfile Load(string root, Manifest manifest)
        {
            bool enabled = manifest.features != null && manifest.features.venue_lighting_identity;
            var tagged = manifest.lights.Select((light, index) => new { light, index }).Where(x => x.light.venueLighting != null).ToArray();
            var clones = manifest.materials.Where(x => x.name.StartsWith("VenueLight_", StringComparison.Ordinal)).ToArray();
            if (!enabled)
            {
                Require(manifest.venueLighting == null && tagged.Length == 0 && clones.Length == 0, "disabled feature has active payload");
                return null; // Exact old light/material behavior, no profile read required.
            }
            Require(manifest.features.shop_personality, "requires existing shop personality");
            byte[] bytes = File.ReadAllBytes(root + "/Data/VenueLighting.json");
            var p = JsonUtility.FromJson<VenueLightingProfile>(Encoding.UTF8.GetString(bytes));
            Require(p != null && p.schema == 1 && p.version == "venue-lighting-1" && p.feature == "venue_lighting_identity", "unsupported profile schema/version");
            Require(Same(p.legacyUnityColor, new float[] {1, .52f, .18f}) && Same(p.legacyPreviewColor, new float[] {1, .48f, .16f})
                && p.unityBaseIntensity == 1.65f && p.previewBaseEnergy == 110 && p.rangeMultiplier == 1.25f && p.bounceIntensity == 1.6f,
                "legacy non-venue lighting constants changed");
            Require(p.shops != null && p.shops.Length == 8, "missing exact eight-venue roster");
            var header = manifest.venueLighting;
            Require(header != null && header.schema == 1 && header.profileVersion == p.version && header.profileSha256 == Digest(bytes), "profile/header/hash mismatch");
            Require(manifest.lights.Length == 374 && tagged.Length == 15, "existing fixture count changed");
            var indices = Enumerable.Range(88, 15).ToArray();
            Require(header.ownedLightIndices != null && header.ownedLightIndices.SequenceEqual(indices) && tagged.Select(x => x.index).SequenceEqual(indices), "fixture ownership changed");
            Require(manifest.materials.Select(x => x.name).Distinct().Count() == manifest.materials.Length, "duplicate material");
            var originals = manifest.materials.ToDictionary(x => x.name);
            var expectedEmitters = new List<VenueLightingEmitter>();
            var names = new HashSet<string>(); var keys = new HashSet<string>();
            int fixtureOrdinal = 0;
            for (int i = 0; i < 8; i++)
            {
                var shop = p.shops[i]; string sid = "S" + (i + 1).ToString("D2");
                Require(shop != null && shop.id == sid && shop.fixtures != null && shop.fixtures.Length == Counts[i], "venue/fixture roster changed: " + sid);
                Require(shop.emitters != null && shop.emitters.Length > 0, "missing emitter bindings: " + sid);
                float priorBudget = 0, newBudget = 0; bool readable = false;
                var fixtureIds = new HashSet<string>();
                for (int j = 0; j < shop.fixtures.Length; j++)
                {
                    var fixture = shop.fixtures[j]; string id = sid + "_F" + (j + 1).ToString("D2");
                    Require(fixture != null && fixture.id == id && fixture.manifestIndex == 88 + fixtureOrdinal++, "fixture identity/index changed");
                    Require(fixture.role == "key" || fixture.role == "task" || fixture.role == "accent", "invalid light role");
                    fixtureIds.Add(id);
                    Vector(fixture.localPosition, -10000, 10000, "local position"); Vector(fixture.worldPosition, -10000, 10000, "world position");
                    Vector(fixture.color, 0, 1, "light RGB");
                    Require(fixture.color.Max() == 1 && fixture.color.Min() >= .10f, "unnormalized/extreme light RGB");
                    Scalar(fixture.range, .1f, 12, "range"); Scalar(fixture.strength, .1f, 3, "strength");
                    Scalar(fixture.intensityMultiplier, .5f, 1.15f, "intensity multiplier");
                    if (fixture.role == "key" || fixture.role == "task")
                    {
                        Require(fixture.color.Min() >= .68f, "readable key/task RGB floor"); readable = true;
                    }
                    priorBudget += fixture.strength * Luma(p.legacyUnityColor);
                    newBudget += fixture.strength * fixture.intensityMultiplier * Luma(fixture.color);
                    var actual = manifest.lights[fixture.manifestIndex]; var tag = actual.venueLighting;
                    Vector(actual.position, -10000, 10000, "actual position");
                    Require(Same(actual.position, fixture.worldPosition) && actual.range == fixture.range && actual.strength == fixture.strength, "actual fixture layout/budget drift: " + id);
                    Require(tag != null && tag.schema == 1 && tag.venueId == sid && tag.fixtureId == id && tag.role == fixture.role
                        && Same(tag.color, fixture.color) && tag.intensityMultiplier == fixture.intensityMultiplier, "actual fixture palette drift: " + id);
                }
                Require(readable, "missing readable key/task light");
                Scalar(newBudget / priorBudget, .80f, 1.28f, "RGB-weighted source budget (not lux)");
                foreach (var emitter in shop.emitters)
                {
                    Require(emitter != null && emitter.group != null && emitter.group.StartsWith("Shops/" + sid + "/Personality/", StringComparison.Ordinal), "unowned emitter group");
                    Require(emitter.sourceMaterial == "Food_Paper" || emitter.sourceMaterial == "RedLantern" || emitter.sourceMaterial == "WarmWindow" || emitter.sourceMaterial == "Ceramic", "unreviewed emitter source");
                    Require(keys.Add(emitter.group + "__" + emitter.sourceMaterial), "duplicate emitter batch binding");
                    Require(emitter.material != null && emitter.material.StartsWith("VenueLight_" + sid + "_", StringComparison.Ordinal) && names.Add(emitter.material), "unowned/duplicate emitter material");
                    Require(emitter.fixtureIds != null && emitter.fixtureIds.Distinct().Count() == emitter.fixtureIds.Length && emitter.fixtureIds.All(x => fixtureIds.Contains(x)), "unknown emitter fixture");
                    Vector(emitter.color, 0, 1, "emitter RGB"); Scalar(emitter.emission, .05f, 1, "emitter emission");
                    if (emitter.fixtureIds.Length == 0) Require(emitter.emission <= .4f, "architectural emission-only accent budget");
                    else
                    {
                        var selected = shop.fixtures.Where(x => emitter.fixtureIds.Contains(x.id)).ToArray();
                        for (int channel = 0; channel < 3; channel++) Require(Math.Abs(emitter.color[channel] - selected.Average(x => x.color[channel])) <= .000001f, "diffuser/fixture palette mismatch");
                    }
                    Require(emitter.shader == "Surface" || emitter.shader == "LanternPaper", "unreviewed emitter shader");
                    Require(emitter.breath == 0, "venue fixtures must remain static"); Scalar(emitter.paperRelief, 0, .045f, "paper relief");
                    var shader = Shader.Find("TreeTopYokocho/" + emitter.shader);
                    Require(shader != null, "emitter shader has not imported");
                    if (emitter.shader == "LanternPaper")
                    {
                        Material probe = null;
                        try
                        {
                            probe = new Material(shader);
                            Require(probe.HasProperty("_Breath") && probe.HasProperty("_PaperRelief"), "missing emitter paper properties");
                        }
                        finally { if (probe != null) UnityEngine.Object.DestroyImmediate(probe); }
                    }
                    Require(originals.ContainsKey(emitter.sourceMaterial) && originals.ContainsKey(emitter.material), "missing actual emitter source/clone");
                    var expected = JsonUtility.FromJson<MaterialSpec>(JsonUtility.ToJson(originals[emitter.sourceMaterial]));
                    expected.name = emitter.material; expected.color = emitter.color; expected.emission = emitter.emission; expected.shader = emitter.shader;
                    Require(JsonUtility.ToJson(expected) == JsonUtility.ToJson(originals[emitter.material]), "emitter clone changed unrelated material fields");
                    expectedEmitters.Add(emitter);
                }
            }
            Require(clones.Length == names.Count && clones.All(x => names.Contains(x.name)), "unexpected material clone");
            Require(header.emitterBindings != null && header.emitterBindings.Length == expectedEmitters.Count, "emitter header count mismatch");
            for (int i = 0; i < expectedEmitters.Count; i++) Require(JsonUtility.ToJson(header.emitterBindings[i]) == JsonUtility.ToJson(expectedEmitters[i]), "emitter header routing mismatch");
            return p;
        }

        public void ApplyMaterial(Material material, MaterialSpec spec)
        {
            var binding = shops.SelectMany(x => x.emitters).FirstOrDefault(x => x.material == spec.name);
            if (binding == null) return;
            Require(material.shader.name == "TreeTopYokocho/" + binding.shader, "clone routed to incorrect shader");
            if (binding.shader == "LanternPaper")
            {
                Require(material.HasProperty("_Breath") && material.HasProperty("_PaperRelief"), "missing emitter paper properties");
                material.SetFloat("_Breath", 0); material.SetFloat("_PaperRelief", binding.paperRelief);
            }
        }
        public static Color LightColor(LightSpec spec)
        {
            return spec.venueLighting == null ? new Color(1, .52f, .18f) : RGB(spec.venueLighting.color);
        }
        public static float Intensity(LightSpec spec)
        {
            return spec.strength * 1.65f * (spec.venueLighting == null ? 1f : spec.venueLighting.intensityMultiplier);
        }
    }
}
#endif

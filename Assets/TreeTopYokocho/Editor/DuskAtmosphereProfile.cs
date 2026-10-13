#if UNITY_EDITOR && !COMPILER_UDONSHARP
using System;
using System.IO;
using System.Text;
using UnityEngine;

namespace TreeTopYokocho.Editor
{
    // Editor input only. It creates no runtime MonoBehaviour or Udon program.
    [Serializable] public sealed class DuskSky
    {
        public float[] horizon, zenith, sunsetDirection, sunsetColor, cloudThreshold, cloudTint;
        public float strength, altitudePower, sunsetPower, sunsetHeight, sunsetWidth;
        public float cloudScale, cloudStretch, cloudHeight, cloudOpacity, cloudShade;
    }
    [Serializable] public sealed class DuskAmbient
    {
        public float[] sky, equator, ground;
        public float intensity, blenderDiffuseStrength;
    }
    [Serializable] public sealed class DuskFog { public float density, comparisonDensity; public float[] color; }
    [Serializable] public sealed class DuskLight
    {
        // Source XYZ / Z up, from the surface toward the light, not ray travel.
        public float[] towardLight, color;
        public float unityIntensity, blenderEnergy, blenderAngle;
    }
    [Serializable] public sealed class DuskDisplay
    {
        public string blenderTransform, unityTonemapper;
        public float blenderExposure, unityPostExposure, unityTemperature, unitySaturation;
    }
    [Serializable] public sealed class DuskAtmosphereProfile
    {
        public int schema;
        public string name, coordinateSystem, colorSpace;
        public DuskSky sky;
        public DuskAmbient ambient;
        public DuskFog fog;
        public DuskLight key, fill;
        public DuskDisplay display;

        static bool Finite(float n) { return !float.IsNaN(n) && !float.IsInfinity(n); }
        static void Vector(float[] value, string field, int size = 3)
        {
            if (value == null || value.Length != size) throw new InvalidDataException("Invalid dusk atmosphere vector: " + field);
            foreach (float n in value) if (!Finite(n)) throw new InvalidDataException("Non-finite dusk atmosphere value: " + field);
        }
        // Ambient and Light.color preserve authored Unity Color API values.
        // Sky uses raw vectors; fog converts linear radiance to the API colour.
        public static Vector4 LinearRGB(float[] c) { return new Vector4(c[0], c[1], c[2], 1); }
        static void FiniteScalars(object section)
        {
            foreach (var field in section.GetType().GetFields())
                if (field.FieldType == typeof(float) && !Finite((float)field.GetValue(section)))
                    throw new InvalidDataException("Non-finite dusk scalar: " + field.Name);
        }
        public static Color RGB(float[] c) { return new Color(c[0], c[1], c[2], 1); }
        public static DuskAtmosphereProfile Load(string root)
        {
            string path = root + "/Data/DuskAtmosphere.json";
            var p = JsonUtility.FromJson<DuskAtmosphereProfile>(File.ReadAllText(path, Encoding.UTF8));
            if (p == null || p.schema != 1 || p.sky == null || p.ambient == null || p.fog == null || p.key == null || p.fill == null || p.display == null)
                throw new InvalidDataException("Missing/unsupported shared dusk atmosphere profile: " + path);
            foreach (object section in new object[] { p.sky, p.ambient, p.fog, p.key, p.fill, p.display }) FiniteScalars(section);
            Vector(p.sky.horizon, "sky.horizon"); Vector(p.sky.zenith, "sky.zenith");
            Vector(p.sky.sunsetDirection, "sky.sunsetDirection"); Vector(p.sky.sunsetColor, "sky.sunsetColor");
            Vector(p.sky.cloudTint, "sky.cloudTint"); Vector(p.sky.cloudThreshold, "sky.cloudThreshold", 2);
            Vector(p.ambient.sky, "ambient.sky"); Vector(p.ambient.equator, "ambient.equator"); Vector(p.ambient.ground, "ambient.ground");
            Vector(p.fog.color, "fog.color");
            foreach (var light in new[] { p.key, p.fill }) {
                Vector(light.towardLight, "light.towardLight"); Vector(light.color, "light.color");
                if (YokochoWorldBuilder.U(light.towardLight).sqrMagnitude < .000001f || !Finite(light.unityIntensity) || light.unityIntensity < 0)
                    throw new InvalidDataException("Invalid dusk directional light.");
            }
            if (!Finite(p.fog.density) || p.fog.density < 0 || p.fog.density > .01f
                || !(p.sky.altitudePower > 0) || !(p.sky.sunsetWidth > 0) || !(p.sky.sunsetPower > 0)
                || !(p.sky.strength > 0) || !(p.sky.cloudScale > 0) || !(p.sky.cloudStretch > 0)
                || !(p.sky.cloudHeight > 0) || !(p.sky.cloudThreshold[1] > p.sky.cloudThreshold[0])
                || p.sky.cloudOpacity < 0 || p.sky.cloudOpacity > 1 || p.sky.cloudShade < 0 || p.sky.cloudShade > 1
                || new Vector2(p.sky.sunsetDirection[0], p.sky.sunsetDirection[1]).sqrMagnitude < .000001f)
                throw new InvalidDataException("Invalid dusk sky/fog shape.");
            if (p.display.unityTonemapper != "ACES" || p.display.blenderTransform != "AgX")
                throw new InvalidDataException("The verified dusk display contract requires Unity ACES and Blender AgX.");
            return p;
        }
        public void ApplySky(Material material)
        {
            // The source sunset azimuth (x,y) becomes Unity horizontal (x,z).
            Vector3 direction = YokochoWorldBuilder.U(sky.sunsetDirection).normalized;
            material.SetVector("_Horizon", LinearRGB(sky.horizon)); material.SetVector("_Zenith", LinearRGB(sky.zenith));
            material.SetFloat("_SkyStrength", sky.strength); material.SetFloat("_AltitudePower", sky.altitudePower);
            material.SetVector("_SunsetDirection", new Vector4(direction.x, direction.y, direction.z, 0));
            material.SetVector("_SunsetColor", LinearRGB(sky.sunsetColor));
            material.SetVector("_SunsetShape", new Vector4(sky.sunsetPower, sky.sunsetHeight, sky.sunsetWidth, 0));
            material.SetVector("_HighCloudShape", new Vector4(sky.cloudThreshold[0], sky.cloudThreshold[1], sky.cloudHeight, sky.cloudOpacity));
            material.SetVector("_HighCloudDetail", new Vector4(sky.cloudScale, sky.cloudStretch, sky.cloudShade, 0));
            material.SetVector("_HighCloudTint", LinearRGB(sky.cloudTint));
        }
        public static void ApplyLight(Light light, DuskLight spec)
        {
            Vector3 towardLight = YokochoWorldBuilder.U(spec.towardLight).normalized;
            light.transform.rotation = Quaternion.LookRotation(-towardLight, Vector3.up);
            light.color = RGB(spec.color); light.intensity = spec.unityIntensity;
        }
    }
}
#endif

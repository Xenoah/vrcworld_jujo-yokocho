Shader "TreeTopYokocho/Surface"
{
    Properties
    {
        _MainTex ("Albedo / sRGB", 2D) = "white" {}
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
        _Color ("Tint", Color) = (1,1,1,1)
        _BumpMap ("Normal / OpenGL", 2D) = "bump" {}
        _NormalStrength ("Normal strength", Range(0,2)) = 1
        _ARM ("R: AO, G: Roughness, B: Metal", 2D) = "white" {}
        _HeightMap ("Height", 2D) = "gray" {}
        _Parallax ("Relief (metres)", Range(0,.06)) = 0
        _Roughness ("Roughness multiplier", Range(0,1)) = .8
        _Metallic ("Metallic multiplier", Range(0,1)) = 0
        _GrainRoughness ("Albedo-driven roughness variation", Range(0,.25)) = 0
        _Patina ("Nonmetal recess patina", Range(0,.35)) = 0
        _Emission ("Emission", Range(0,8)) = 0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        LOD 400
        Cull [_Cull]
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow
        #pragma target 3.0
        #pragma multi_compile_instancing
        #pragma shader_feature_local _YOKOCHO_NORMALMAP
        #pragma shader_feature_local _YOKOCHO_ARM
        #pragma shader_feature_local _YOKOCHO_CRAFT
        #pragma shader_feature_local _YOKOCHO_PARALLAX
        #include "UnityCG.cginc"
        sampler2D _MainTex, _BumpMap, _ARM, _HeightMap;
        fixed4 _Color;
        half _Roughness, _Metallic, _Emission, _NormalStrength, _Parallax, _GrainRoughness, _Patina;
        struct Input { float2 uv_MainTex; float3 viewDir; float4 color:COLOR; };
        void surf(Input IN, inout SurfaceOutputStandard o)
        {
            float2 uv=IN.uv_MainTex;
            #if defined(_YOKOCHO_PARALLAX)
            if(_Parallax>.0001) {
                half h=tex2D(_HeightMap,uv).r;
                uv+=ParallaxOffset(h,_Parallax,IN.viewDir);
            }
            #endif
            fixed4 albedo=tex2D(_MainTex,uv)*_Color;
            half3 arm=half3(1,1,1);
            #if defined(_YOKOCHO_ARM)
            arm=tex2D(_ARM,uv).rgb;
            #endif
            o.Albedo=albedo.rgb*IN.color.rgb;
            #if defined(_YOKOCHO_NORMALMAP)
            half3 normal=UnpackNormal(tex2D(_BumpMap,uv));
            normal.xy*=_NormalStrength; o.Normal=normalize(normal);
            #endif
            o.Occlusion=arm.r;
            o.Metallic=saturate(arm.b*_Metallic);
            o.Smoothness=saturate(1-arm.g*_Roughness);
            #if defined(_YOKOCHO_CRAFT)
            // Reuse sampled texture detail: no extra normal, mask or noise fetch.
            // Patina uses the packed AO, never vertex AO (which can be lighting).
            half grain = dot(albedo.rgb,half3(.2126,.7152,.0722));
            half patina = saturate(1-arm.r)*clamp(_Patina,0,.35);
            o.Smoothness = saturate(o.Smoothness+(grain-.5)*clamp(_GrainRoughness,0,.25)-patina*.25);
            o.Metallic *= 1-patina;
            #endif
            o.Emission=albedo.rgb*_Emission;
            o.Alpha=1;
        }
        ENDCG
    }
    FallBack "Standard"
}

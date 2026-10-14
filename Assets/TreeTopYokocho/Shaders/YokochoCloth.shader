// Opaque woven cloth: no alpha blending, deformation, extra lights or handwritten passes.
Shader "TreeTopYokocho/Cloth"
{
    Properties
    {
        _MainTex ("Woven colour / sRGB", 2D) = "white" {}
        _Color ("Authored tint", Color) = (1,1,1,1)
        _BumpMap ("Cloth normal", 2D) = "bump" {}
        _ARM ("AO / Roughness / unused", 2D) = "white" {}
        _Roughness ("Roughness", Range(0,1)) = .95
        _NormalStrength ("Normal strength", Range(0,2)) = 1
        _WeaveScale ("Procedural cycles per UV repeat", Range(8,4096)) = 96
        _WeaveStrength ("Thread normal strength", Range(0,.15)) = .045
        _Sheen ("Soft grazing reflectance", Range(0,.12)) = .055
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Cull [_Cull]
        CGPROGRAM
        #pragma surface surf StandardSpecular fullforwardshadows addshadow
        #pragma target 3.0
        #pragma multi_compile_instancing
        #pragma shader_feature_local _YOKOCHO_NORMALMAP
        #pragma shader_feature_local _YOKOCHO_ARM
        #include "UnityCG.cginc"
        sampler2D _MainTex, _BumpMap, _ARM;
        fixed4 _Color;
        half _Roughness, _NormalStrength, _WeaveScale, _WeaveStrength, _Sheen;
        struct Input { float2 uv_MainTex; float4 color:COLOR; float3 viewDir; float facing:VFACE; };
        void surf(Input IN, inout SurfaceOutputStandardSpecular o)
        {
            float2 uv = IN.uv_MainTex;
            fixed3 color = tex2D(_MainTex,uv).rgb * _Color.rgb * IN.color.rgb;
            half3 n = half3(0,0,1);
            #if defined(_YOKOCHO_NORMALMAP)
            n = UnpackNormal(tex2D(_BumpMap,uv));
            n.xy *= _NormalStrength;
            #endif
            // Fade before Nyquist instead of shimmering against the two VR eyes.
            float2 thread = uv * _WeaveScale;
            float footprint = max(fwidth(thread.x), fwidth(thread.y));
            float resolved = 1.0-smoothstep(.20,.50,footprint);
            float2 wave = sin(thread * 6.2831853);
            n.xy += wave * (_WeaveStrength * resolved);
            n.z *= IN.facing > 0 ? 1 : -1;
            o.Normal = normalize(n);
            half3 arm = half3(1,1,1);
            #if defined(_YOKOCHO_ARM)
            arm = tex2D(_ARM,uv).rgb;
            #endif
            half grazing = 0;
            #if !defined(UNITY_PASS_META)
            grazing = pow(1.0-saturate(abs(dot(normalize(IN.viewDir),o.Normal))),4.0);
            #endif
            o.Albedo = color;
            // Light-driven sheen, not emissive rim lighting. Preserves dark cloth.
            o.Specular = half3(.025,.025,.025) + saturate(_Sheen)*grazing;
            o.Smoothness = clamp(1.0-arm.g*_Roughness, .04, .28);
            o.Occlusion = arm.r;
            o.Emission = 0;
            o.Alpha = 1;
        }
        ENDCG
    }
    FallBack "Standard (Specular setup)"
}

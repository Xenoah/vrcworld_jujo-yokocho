// Solid glazed ceramic / opaque bottles, not a glass/refraction replacement.
Shader "TreeTopYokocho/Glaze"
{
    Properties
    {
        _MainTex ("Glaze colour / sRGB", 2D) = "white" {}
        _Color ("Authored tint", Color) = (1,1,1,1)
        _BumpMap ("Surface normal", 2D) = "bump" {}
        _ARM ("AO / Roughness / Metal", 2D) = "white" {}
        _NormalStrength ("Normal strength", Range(0,2)) = 1
        _Roughness ("Glaze roughness", Range(0,1)) = .2
        _Metallic ("Authored metallic mix", Range(0,1)) = 0
        _Iridescence ("Restrained film tint", Range(0,.25)) = .18
        _FilmCycles ("Film colour variation", Range(.2,2)) = .75
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Cull Back
        CGPROGRAM
        #pragma surface surf StandardSpecular fullforwardshadows addshadow
        #pragma target 3.0
        #pragma multi_compile_instancing
        #pragma shader_feature_local _YOKOCHO_NORMALMAP
        #pragma shader_feature_local _YOKOCHO_ARM
        #include "UnityCG.cginc"
        sampler2D _MainTex, _BumpMap, _ARM;
        fixed4 _Color;
        half _NormalStrength, _Roughness, _Metallic, _Iridescence, _FilmCycles;
        struct Input { float2 uv_MainTex; float3 viewDir; float4 color:COLOR; };
        void surf(Input IN,inout SurfaceOutputStandardSpecular o)
        {
            half3 color=tex2D(_MainTex,IN.uv_MainTex).rgb*_Color.rgb*IN.color.rgb;
            half3 n=half3(0,0,1);
            #if defined(_YOKOCHO_NORMALMAP)
            n=UnpackNormal(tex2D(_BumpMap,IN.uv_MainTex));n.xy*=_NormalStrength;
            #endif
            o.Normal=normalize(n);
            half3 arm=half3(1,1,1);
            #if defined(_YOKOCHO_ARM)
            arm=tex2D(_ARM,IN.uv_MainTex).rgb;
            #endif
            half metal=saturate(arm.b*_Metallic);
            half ndv=1;
            #if !defined(UNITY_PASS_META)
            ndv=saturate(abs(dot(normalize(IN.viewDir),o.Normal)));
            #endif
            half grazing=(1-ndv)*(1-ndv);
            // Gentle view-dependent film colour, reflected light only. No
            // temporal animation or emissive edges; peak F0 change is ±10%.
            half phase=(1-ndv)*clamp(_FilmCycles,.2,2)*6.2831853;
            half3 film=.5+.5*cos(phase+half3(0,2.0943951,4.1887902));
            half3 reflectance=lerp(half3(.04,.04,.04),saturate(color),metal);
            reflectance*=lerp(half3(1,1,1),.6+.8*film,clamp(_Iridescence,0,.25)*grazing*(1-metal));
            o.Specular=saturate(reflectance);
            // Specular workflow handles dielectric energy conservation; remove
            // the diffuse metal share as the metallic workflow normally does.
            o.Albedo=color*(1-metal);
            o.Smoothness=clamp(1-arm.g*_Roughness,.08,.92);
            o.Occlusion=arm.r;o.Emission=0;o.Alpha=1;
        }
        ENDCG
    }
    FallBack "Standard (Specular setup)"
}

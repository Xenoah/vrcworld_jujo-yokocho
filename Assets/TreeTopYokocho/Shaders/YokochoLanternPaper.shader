Shader "TreeTopYokocho/LanternPaper"
{
    Properties
    {
        _MainTex ("Paper and painted ink / sRGB", 2D) = "white" {}
        _Color ("Authored tint", Color) = (1,1,1,1)
        _Emission ("Base baked radiance", Range(0,8)) = 1.3
        _Roughness ("Paper roughness", Range(0,1)) = .8
        _Breath ("Slow light variation", Range(0,.03)) = .015
        _PaperRelief ("Paper fibre shading", Range(0,.15)) = .045
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        Cull Back
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow
        #pragma target 3.0
        #pragma multi_compile_instancing
        #include "UnityCG.cginc"
        sampler2D _MainTex;
        fixed4 _Color;
        half _Emission, _Roughness, _Breath, _PaperRelief;
        struct Input { float2 uv_MainTex; float4 color:COLOR; };
        void surf(Input IN,inout SurfaceOutputStandard o)
        {
            fixed3 paper = tex2D(_MainTex, IN.uv_MainTex).rgb * _Color.rgb;
            half fibre = dot(paper,half3(.2126,.7152,.0722));
            o.Albedo = paper * IN.color.rgb;
            o.Metallic = 0;
            o.Smoothness = saturate(1.0-_Roughness)*(1.0-saturate(_PaperRelief)*fibre);
            o.Occlusion = 1;
            // Meta pass bakes the steady base only, never a time-dependent sample.
            half breath = 1;
            #if !defined(UNITY_PASS_META)
            breath += clamp(_Breath,0,.03)*sin(_Time.y*.31);
            #endif
            // Preserve ink and existing emission semantics (vertex AO does not
            // darken internally lit paper). No new realtime light is needed.
            o.Emission = paper * max(0,_Emission) * breath;
            o.Alpha = 1;
        }
        ENDCG
    }
    FallBack "Standard"
}

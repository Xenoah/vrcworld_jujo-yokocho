Shader "TreeTopYokocho/Water"
{
    Properties
    {
        _MainTex ("Water colour", 2D) = "white" {}
        _BumpMap ("Ripples", 2D) = "bump" {}
        _Color ("Water tint", Color) = (.09,.19,.24,1)
        _Roughness ("Roughness", Range(0,1)) = .19
        _Metallic ("Reflection", Range(0,1)) = .35
    }
    SubShader
    {
        Tags {"RenderType"="Opaque"}
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows vertex:vert addshadow
        #pragma target 3.0
        #pragma multi_compile_instancing
        #include "UnityCG.cginc"
        sampler2D _MainTex,_BumpMap;fixed4 _Color;half _Roughness,_Metallic;
        struct Input { float2 uv_MainTex; float3 viewDir; };
        void vert(inout appdata_full v) {
            v.vertex.y+=sin(v.vertex.x*.13+_Time.y*.4)*.025+sin(v.vertex.z*.19-_Time.y*.28)*.018;
        }
        void surf(Input IN,inout SurfaceOutputStandard o) {
            float2 uv=IN.uv_MainTex;
            half3 a=UnpackNormal(tex2D(_BumpMap,uv+float2(_Time.y*.003,_Time.y*.002)));
            half3 b=UnpackNormal(tex2D(_BumpMap,uv*1.7+float2(-_Time.y*.002,_Time.y*.001)));
            o.Normal=normalize(half3(a.xy+b.xy,a.z*b.z));
            o.Albedo=tex2D(_MainTex,uv*.25).rgb*_Color.rgb;
            o.Smoothness=1-_Roughness;o.Metallic=_Metallic;o.Occlusion=1;o.Alpha=1;
        }
        ENDCG
    }
    FallBack "Standard"
}

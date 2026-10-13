Shader "TreeTopYokocho/Foliage"
{
    Properties
    {
        _MainTex ("Leaf colour", 2D) = "white" {}
        _Color ("Tint", Color) = (1,1,1,1)
        _BumpMap ("Leaf veins", 2D) = "bump" {}
        _ARM ("AO / Roughness / Metal", 2D) = "white" {}
        _Roughness ("Roughness", Range(0,1)) = .8
        _Cutoff ("Alpha cutoff", Range(0,1)) = .4
        _Wind ("Wind amplitude", Range(0,.08)) = .018
    }
    SubShader
    {
        Tags { "RenderType"="TransparentCutout" "Queue"="AlphaTest" }
        Cull Off
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows vertex:vert addshadow alphatest:_Cutoff
        #pragma target 3.0
        #pragma multi_compile_instancing
        #pragma shader_feature_local _YOKOCHO_NORMALMAP
        #pragma shader_feature_local _YOKOCHO_ARM
        #include "UnityCG.cginc"
        sampler2D _MainTex,_BumpMap,_ARM;
        fixed4 _Color;half _Roughness,_Wind;
        struct Input {float2 uv_MainTex; float4 color:COLOR; float facing:VFACE;};
        void vert(inout appdata_full v) {
            float3 p=mul(unity_ObjectToWorld,v.vertex).xyz;
            float w=sin(_Time.y*.8+p.x*.42+p.z*.31)+.4*sin(_Time.y*1.7+p.y*.73);
            v.vertex.xz+=float2(w,w*.44)*_Wind*v.texcoord.y;
        }
        void surf(Input IN,inout SurfaceOutputStandard o) {
            fixed4 a=tex2D(_MainTex,IN.uv_MainTex);fixed3 c=a.rgb*_Color.rgb*IN.color.rgb;
            o.Albedo=c;
            half3 n=half3(0,0,1);
            #if defined(_YOKOCHO_NORMALMAP)
            n=UnpackNormal(tex2D(_BumpMap,IN.uv_MainTex));
            #endif
            n.z*=IN.facing>0?1:-1;o.Normal=normalize(n);
            half3 arm=half3(1,1,1);
            #if defined(_YOKOCHO_ARM)
            arm=tex2D(_ARM,IN.uv_MainTex).rgb;
            #endif
            o.Occlusion=arm.r;o.Smoothness=saturate(1-arm.g*_Roughness);o.Metallic=0;
            o.Emission=c*.035;o.Alpha=a.a*_Color.a;
        }
        ENDCG
    }
    FallBack "Standard"
}

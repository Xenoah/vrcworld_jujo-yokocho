Shader "TreeTopYokochoEntrySystems/DepthTestedStatusText"
{
    Properties { _MainTex("Font atlas",2D)="white" {} _Color("Tint",Color)=(1,1,1,1) }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" }
        Blend SrcAlpha OneMinusSrcAlpha
        ZWrite Off ZTest LEqual Cull Off
        Pass
        {
            CGPROGRAM
            #pragma target 3.0
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            sampler2D _MainTex; float4 _Color;
            struct a {float4 vertex:POSITION;float2 uv:TEXCOORD0;float4 color:COLOR;UNITY_VERTEX_INPUT_INSTANCE_ID};
            struct v {float4 position:SV_POSITION;float2 uv:TEXCOORD0;float4 color:COLOR;UNITY_VERTEX_OUTPUT_STEREO};
            v vert(a i) {v o; UNITY_SETUP_INSTANCE_ID(i);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);o.position=UnityObjectToClipPos(i.vertex);o.uv=i.uv;o.color=i.color*_Color;return o;}
            fixed4 frag(v i):SV_Target {UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);return fixed4(i.color.rgb,i.color.a*tex2D(_MainTex,i.uv).a);}
            ENDCG
        }
    }
}

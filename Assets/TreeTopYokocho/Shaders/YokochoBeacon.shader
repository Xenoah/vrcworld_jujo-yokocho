Shader "TreeTopYokocho/Beacon"
{
    Properties
    {
        [HDR] _Color("Warning red", Color)=(1,0.015,0.004,1)
        _Emission("Peak emission", Float)=10
        _Period("Flash period seconds", Range(0.5,8))=2
        _Duty("Lit fraction", Range(0.05,0.5))=0.16
        _Phase("Phase offset", Range(0,1))=0
    }
    SubShader
    {
        Tags {"RenderType"="Opaque" "Queue"="Geometry"}
        Pass
        {
            CGPROGRAM
            #pragma target 3.0
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            float4 _Color;
            float _Emission,_Period,_Duty,_Phase;
            struct appdata { float4 vertex:POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v2f { float4 vertex:SV_POSITION; UNITY_FOG_COORDS(0) UNITY_VERTEX_OUTPUT_STEREO };
            v2f vert(appdata v)
            {
                v2f o; UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_OUTPUT(v2f,o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.vertex=UnityObjectToClipPos(v.vertex); UNITY_TRANSFER_FOG(o,o.vertex); return o;
            }
            float4 frag(v2f i):SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float phase=frac(_Time.y/max(_Period,0.5)+_Phase);
                float edge=min(0.025,_Duty*0.2);
                float pulse=smoothstep(0,edge,phase)*(1-smoothstep(_Duty-edge,_Duty,phase));
                float4 c=float4(_Color.rgb*(0.08+max(0,_Emission)*pulse),1);
                UNITY_APPLY_FOG(i.fogCoord,c);return c;
            }
            ENDCG
        }
    }
    Fallback "Unlit/Color"
}

Shader "TreeTopYokocho/BlueHourSky"
{
    Properties
    {
        _Zenith("Zenith",Color)=(.012,.034,.085,1)
        _Horizon("Horizon",Color)=(.17,.23,.34,1)
    }
    SubShader
    {
        Tags { "Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox" }
        Cull Off ZWrite Off
        Pass
        {
            CGPROGRAM
            #pragma target 3.0
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"
            float4 _Zenith,_Horizon;
            struct a { float4 vertex:POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v { float4 pos:SV_POSITION; float3 dir:TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };
            v vert(a i) { v o; UNITY_SETUP_INSTANCE_ID(i); UNITY_INITIALIZE_OUTPUT(v,o); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o); o.pos=UnityObjectToClipPos(i.vertex); o.dir=i.vertex.xyz; return o; }
            float hash(float2 p) {return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
            float noise(float2 p) {float2 k=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(k),hash(k+float2(1,0)),f.x),lerp(hash(k+float2(0,1)),hash(k+float2(1,1)),f.x),f.y);}
            float fbm(float2 p) {float value=0,amplitude=.5;for(int i=0;i<5;i++){value+=noise(p)*amplitude;p=p*2.07+17.3;amplitude*=.5;}return value;}
            fixed4 frag(v i):SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 d=normalize(i.dir);float t=pow(saturate(d.y),.46);
                float3 c=lerp(_Horizon.rgb,_Zenith.rgb,t);
                float sunset=pow(saturate(dot(normalize(d.xz+float2(.00001,.00001)),normalize(float2(-.8,.6)))),6);
                c+=float3(.26,.085,.033)*exp(-pow((d.y-.035)*12,2))*sunset;
                float2 p=d.xz/max(.11,d.y+.2)*2.5;
                float cloud=smoothstep(.48,.70,fbm(p*float2(1,3.2)));
                c=lerp(c,c*.55+float3(.007,.008,.012),cloud*smoothstep(0,.14,d.y)*.75);
                return float4(c,1);
            }
            ENDCG
        }
    }
}

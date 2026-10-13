Shader "TreeTopYokocho/BlueHourSky"
{
    Properties
    {
        _Zenith("Zenith scene-linear RGB",Vector)=(.012,.034,.085,1)
        _Horizon("Horizon scene-linear RGB",Vector)=(.17,.23,.34,1)
        _SkyStrength("Visible and reflected radiance",Float)=1
        _AltitudePower("Altitude curve",Float)=.46
        _SunsetDirection("Sunset toward-light Unity XYZ",Vector)=(-.8,0,.6,0)
        _SunsetColor("Sunset scene-linear RGB",Vector)=(.26,.085,.033,1)
        _SunsetShape("Sunset power, height, width",Vector)=(6,.035,12,0)
        _HighCloudShape("Cloud threshold low/high, height, opacity",Vector)=(.48,.70,.14,.75)
        _HighCloudDetail("Cloud scale, stretch, shade",Vector)=(2.5,3.2,.55,0)
        _HighCloudTint("High-cloud scene-linear RGB",Vector)=(.007,.008,.012,1)
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
            // Values are authored once in Data/DuskAtmosphere.json by the editor.
            // Same five-octave sky, no new samples, passes, textures or runtime scripts.
            float4 _Zenith,_Horizon,_SunsetDirection,_SunsetColor,_SunsetShape;
            float4 _HighCloudShape,_HighCloudDetail,_HighCloudTint;
            float _SkyStrength,_AltitudePower;
            struct a { float4 vertex:POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v { float4 pos:SV_POSITION; float3 dir:TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };
            v vert(a i) { v o; UNITY_SETUP_INSTANCE_ID(i); UNITY_INITIALIZE_OUTPUT(v,o); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o); o.pos=UnityObjectToClipPos(i.vertex); o.dir=i.vertex.xyz; return o; }
            float hash(float2 p) {return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
            float noise(float2 p) {float2 k=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(k),hash(k+float2(1,0)),f.x),lerp(hash(k+float2(0,1)),hash(k+float2(1,1)),f.x),f.y);}
            float fbm(float2 p) {float value=0,amplitude=.5;for(int i=0;i<5;i++){value+=noise(p)*amplitude;p=p*2.07+17.3;amplitude*=.5;}return value;}
            fixed4 frag(v i):SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 d=normalize(i.dir);float t=pow(saturate(d.y),_AltitudePower);
                float3 c=lerp(_Horizon.rgb,_Zenith.rgb,t);
                float sunset=pow(saturate(dot(normalize(d.xz+float2(.00001,.00001)),normalize(_SunsetDirection.xz))),_SunsetShape.x);
                c+=_SunsetColor.rgb*exp(-pow((d.y-_SunsetShape.y)*_SunsetShape.z,2))*sunset;
                float2 p=d.xz/max(.11,d.y+.2)*_HighCloudDetail.x;
                float cloud=smoothstep(_HighCloudShape.x,_HighCloudShape.y,fbm(p*float2(1,_HighCloudDetail.y)));
                c=lerp(c,c*_HighCloudDetail.z+_HighCloudTint.rgb,cloud*smoothstep(0,_HighCloudShape.z,d.y)*_HighCloudShape.w);
                return float4(c*_SkyStrength,1);
            }
            ENDCG
        }
    }
}

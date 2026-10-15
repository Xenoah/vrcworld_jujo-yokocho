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
        _StarStrength("Stable starlight scene-linear", Range(0,.2)) = .045
        _AuroraStrength("Aurora scene-linear radiance", Range(0,.15)) = .035
        _AuroraColor("Aurora scene-linear RGB", Vector) = (.10,.48,.42,0)
        _AuroraDirection("Aurora horizontal direction", Vector) = (0,0,1,0)
        _AuroraHeight("Aurora direction Y centre", Range(.15,.65)) = .27
        _AuroraWidth("Aurora band falloff", Range(16,60)) = 38
        _AuroraMotion("Aurora drift radians/sec", Range(0,.025)) = .012
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
            #pragma shader_feature_local _YOKOCHO_FANTASY_SKY
            #include "UnityCG.cginc"
            // Values are authored once in Data/DuskAtmosphere.json by the editor.
            // Existing five-octave sky; optional fantasy adds ALU only, no textures,
            // passes, scene shells or runtime scripts. Profile values are linear.
            float4 _Zenith,_Horizon,_SunsetDirection,_SunsetColor,_SunsetShape;
            float4 _HighCloudShape,_HighCloudDetail,_HighCloudTint;
            float _SkyStrength,_AltitudePower;
            float _StarStrength,_AuroraStrength,_AuroraMotion,_AuroraHeight,_AuroraWidth;
            float4 _AuroraColor,_AuroraDirection;
            struct a { float4 vertex:POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct v { float4 pos:SV_POSITION; float3 dir:TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };
            v vert(a i) { v o; UNITY_SETUP_INSTANCE_ID(i); UNITY_INITIALIZE_OUTPUT(v,o); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o); o.pos=UnityObjectToClipPos(i.vertex); o.dir=i.vertex.xyz; return o; }
            float hash(float2 p) {return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
            float noise(float2 p) {float2 k=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(k),hash(k+float2(1,0)),f.x),lerp(hash(k+float2(0,1)),hash(k+float2(1,1)),f.x),f.y);}
            float fbm(float2 p) {float value=0,amplitude=.5;for(int i=0;i<5;i++){value+=noise(p)*amplitude;p=p*2.07+17.3;amplitude*=.5;}return value;}
            // Sparse, fixed stars. Derivative-sized soft coverage suppresses
            // subpixel sparkle; no temporal random seeds or blinking particles.
            float stars(float3 d)
            {
                float2 uv = float2(atan2(d.z,d.x)/6.2831853+.5,d.y);
                float2 grid = uv*float2(256,112);
                float2 cell = floor(grid), f = frac(grid);
                // Longitude is periodic; wrap cell identity and derivatives at
                // atan2's seam instead of losing stars to a 256-cell footprint.
                cell.x -= floor(cell.x/256.0)*256.0;
                float seed = hash(cell);
                float2 center = .25+.5*float2(hash(cell+17.2),hash(cell+71.6));
                float2 dx=ddx(grid), dy=ddy(grid);
                dx.x -= round(dx.x/256.0)*256.0;
                dy.x -= round(dy.x/256.0)*256.0;
                float width = max(length(abs(dx)+abs(dy)),.035);
                float filterWidth = min(width,.18);
                float radius = .065;
                float starPoint = 1-smoothstep(max(0,radius-filterWidth),radius+filterWidth,length(f-center));
                // Do not amplify intensity as the point becomes subpixel.
                float coverage = saturate(radius/max(width,radius));
                return starPoint*coverage*coverage*step(.983,seed)*smoothstep(.10,.38,d.y)*(1-smoothstep(.80,.98,d.y));
            }
            float aurora(float3 d)
            {
                float angle = atan2(d.x,d.z);
                float drift = _Time.y*clamp(_AuroraMotion,0,.025);
                float wave = sin(angle*3.0+drift)*.032+sin(angle*7.0-drift*.61)*.015;
                float height = clamp(_AuroraHeight,.15,.65)+wave;
                float band = exp(-abs(d.y-height)*clamp(_AuroraWidth,16,60));
                float ribs = .66+.34*sin(angle*31.0+sin(angle*5.0)*2.0+drift);
                float facing = pow(saturate(dot(normalize(d.xz+float2(.00001,.00001)),normalize(_AuroraDirection.xz+float2(.00001,.00001)))),3.0);
                return band*ribs*facing*smoothstep(.08,.18,d.y);
            }
            float4 frag(v i):SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float3 d=normalize(i.dir);float t=pow(saturate(d.y),_AltitudePower);
                float3 c=lerp(_Horizon.rgb,_Zenith.rgb,t);
                float sunset=pow(saturate(dot(normalize(d.xz+float2(.00001,.00001)),normalize(_SunsetDirection.xz))),_SunsetShape.x);
                c+=_SunsetColor.rgb*exp(-pow((d.y-_SunsetShape.y)*_SunsetShape.z,2))*sunset;
                float2 p=d.xz/max(.11,d.y+.2)*_HighCloudDetail.x;
                float cloud=smoothstep(_HighCloudShape.x,_HighCloudShape.y,fbm(p*float2(1,_HighCloudDetail.y)));
                float cover=cloud*smoothstep(0,_HighCloudShape.z,d.y)*_HighCloudShape.w;
                #if defined(_YOKOCHO_FANTASY_SKY)
                c += (stars(d)*clamp(_StarStrength,0,.2)*float3(.75,.85,1.0)
                    + aurora(d)*clamp(_AuroraStrength,0,.15)*max(0,_AuroraColor.rgb))*(1-cover);
                #endif
                c=lerp(c,c*_HighCloudDetail.z+_HighCloudTint.rgb,cover);
                return float4(c*_SkyStrength,1);
            }
            ENDCG
        }
    }
}

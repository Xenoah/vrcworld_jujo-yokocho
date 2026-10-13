Shader "TreeTopYokocho/CloudSea"
{
    Properties
    {
        _Color("Silver-blue cloud", Color) = (.78,.85,.95,1)
        _ShadeColor("Blue-hour shadow", Color) = (.23,.32,.47,1)
        _Opacity("Cloud opacity", Range(0,1)) = .86
        _NoiseScale("World-space noise per metre", Range(.005,.1)) = .024
        _Wind("Wind metres/sec (east, north)", Vector) = (.62,.18,0,0)
        _Swell("Vertical drift metres", Range(0,.15)) = .12
    }
    SubShader
    {
        Tags { "Queue"="Transparent-20" "RenderType"="Transparent" "IgnoreProjector"="True" "DisableBatching"="True" }
        // Exactly one pass; nine small billows per bank; no shadow/depth/GrabPass.
        // Premultiplied alpha prevents dark borders on very soft silhouettes.
        Blend One OneMinusSrcAlpha
        ZWrite Off
        ZTest LEqual
        Cull Off
        Pass
        {
            CGPROGRAM
            #pragma target 3.0
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"

            fixed4 _Color, _ShadeColor;
            float _Opacity, _NoiseScale, _Swell;
            float4 _Wind;

            struct appdata
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct v2f
            {
                float4 vertex : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 world : TEXCOORD1;
                half3 normal : TEXCOORD2;
                UNITY_FOG_COORDS(3)
                UNITY_VERTEX_OUTPUT_STEREO
            };

            // Arithmetic hash avoids large-coordinate sine precision issues.
            float hash21(float2 p)
            {
                float3 q = frac(float3(p.x, p.y, p.x) * .1031);
                q += dot(q, q.yzx + 33.33);
                return frac((q.x + q.y) * q.z);
            }
            // Value and analytic X/Y derivatives from the same four hashes.
            float3 noise2(float2 p)
            {
                float2 cell = floor(p), t = frac(p);
                float2 f = t*t*(3.0-2.0*t), df = 6.0*t*(1.0-t);
                float a = hash21(cell), b = hash21(cell+float2(1,0));
                float c = hash21(cell+float2(0,1)), d = hash21(cell+float2(1,1));
                float value = lerp(lerp(a,b,f.x),lerp(c,d,f.x),f.y);
                float dx = df.x*lerp(b-a,d-c,f.y);
                float dy = df.y*lerp(c-a,d-b,f.x);
                return float3(value,dx,dy);
            }

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_OUTPUT(v2f,o);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                float3 world = mul(unity_ObjectToWorld, v.vertex).xyz;
                float envelope = saturate(1.0-length(v.uv*2.0-1.0));
                // Source +Z is Unity +Y. Stay below 124 m even while animated.
                world.y += sin(_Time.y*.13+world.x*.011+world.z*.014)*_Swell*envelope;
                o.vertex = UnityWorldToClipPos(world);
                o.world = world;
                o.normal = UnityObjectToWorldNormal(v.normal);
                o.uv = v.uv;
                UNITY_TRANSFER_FOG(o,o.vertex);
                return o;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float r = length(i.uv*2.0-1.0);
                float outer = 1.0-smoothstep(.88,1.0,r);
                // Early trim outside the cap saves expensive noise at the edge.
                clip(outer-.003);
                float2 p = (i.world.xz-_Time.y*_Wind.xy)*_NoiseScale;
                float3 coarse = noise2(p);
                float3 fine = noise2(p*2.07+float2(13.1,7.7));
                float3 detail = noise2(p*4.13+float2(31.7,19.3));
                float n = coarse.x*.58+fine.x*.28+detail.x*.14;
                float2 gradient = coarse.yz*.58+fine.yz*.28*2.07+detail.yz*.14*4.13;
                float edge = (1.0-smoothstep(.30,.98,r+(.5-n)*.36))*outer;
                float density = lerp(.32,1.0,saturate((n-.25)/.43));
                float alpha = saturate(edge*density*_Opacity*_Color.a);
                half3 normal = normalize(i.normal-float3(gradient.x,0,gradient.y)*.43);
                float sun = saturate(dot(normal, normalize(float3(-.42,.83,-.35))));
                float light = saturate(.25 + .57*n + .23*sun);
                float3 color = lerp(_ShadeColor.rgb,_Color.rgb,light);
                // A small warm shoulder echoes the scene's last sunset.
                color += float3(.045,.020,.005)*pow(sun,3.0)*smoothstep(.35,.8,n);
                // Ground-side remains soft and blue, not an upside-down bright sheet.
                float above = smoothstep(-5.0,5.0,_WorldSpaceCameraPos.y-i.world.y);
                color *= lerp(.69,1.0,above);
                fixed4 c = fixed4(color,alpha);
                // Apply built-in distance fog before premultiplication so haze
                // cannot restore opacity at the deliberately open bank edges.
                UNITY_APPLY_FOG(i.fogCoord,c);
                c.rgb *= alpha;
                return c;
            }
            ENDCG
        }
    }
    Fallback Off
}

Shader "TreeTopYokocho/Water"
{
    Properties
    {
        _MainTex ("Water colour", 2D) = "white" {}
        _BumpMap ("Ripples", 2D) = "bump" {}
        _Color ("Water tint", Color) = (.09,.19,.24,1)
        _Roughness ("Roughness", Range(0,1)) = .19
        _Metallic ("Reflection", Range(0,1)) = .35
        _RippleScale ("Normal repeats per world metre", Range(.005,.2)) = .035
        _RippleStrength ("Ripple strength", Range(0,.5)) = .12
        _WaveSlope ("Long-wave normal strength", Range(0,.08)) = .018
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "Queue"="Geometry" }
        // YOKOCHO_STATIC_PLANAR_SEA
        // Intentionally no vertex displacement: kilometre-scale sea grids may
        // be simplified without changing wave phase, shoreline or silhouette.
        CGPROGRAM
        #pragma surface surf Standard fullforwardshadows addshadow
        #pragma target 3.0
        #pragma multi_compile_instancing
        #include "UnityCG.cginc"
        sampler2D _MainTex, _BumpMap;
        fixed4 _Color;
        half _Roughness, _Metallic, _RippleScale, _RippleStrength, _WaveSlope;
        struct Input { float2 uv_MainTex; float3 worldPos; float3 worldNormal; INTERNAL_DATA };
        void surf(Input IN,inout SurfaceOutputStandard o)
        {
            float2 p = IN.worldPos.xz;
            float2 uv = p * _RippleScale;
            half3 a = UnpackNormal(tex2D(_BumpMap,uv+float2(_Time.y*.003,_Time.y*.002)));
            // Rotate the second existing sample, and rotate its decoded normal
            // back into the world ripple frame (R transpose, not R).
            float2 uvB=float2(.8*uv.x-.6*uv.y,.6*uv.x+.8*uv.y)*1.7;
            half3 b = UnpackNormal(tex2D(_BumpMap,uvB+float2(-_Time.y*.002,_Time.y*.001)));
            half2 bWorld=half2(.8*b.x+.6*b.y,-.6*b.x+.8*b.y);
            // Bounded analytic slopes stay continuous across mesh/UV seams.
            const float2 directionA=float2(.8,.6), directionB=float2(-.6,.8);
            const float2 warpA=float2(-.6,.8), warpB=float2(.8,.6);
            float2 warpPhase=float2(dot(p,warpA)*.021+_Time.y*.07,
                                    dot(p,warpB)*.017-_Time.y*.05);
            float2 phase=float2(dot(p,directionA)*.13+_Time.y*.4,
                                dot(p,directionB)*.19-_Time.y*.28)
                         +sin(warpPhase)*float2(1.1,.8);
            float2 resolved=1.0-smoothstep(.5,2.0,fwidth(phase));
            // Derivatives include the slow phase warp, preserving a coherent
            // normal field while breaking ruler-straight, axis-aligned bands.
            float2 gradA=directionA+warpA*(.021*1.1/.13)*cos(warpPhase.x);
            float2 gradB=directionB+warpB*(.017*.8/.19)*cos(warpPhase.y);
            float2 slope=(gradA*cos(phase.x)*resolved.x*.65
                         +gradB*cos(phase.y)*resolved.y*.35)*_WaveSlope;
            half2 ripple = (a.xy+bWorld)*_RippleStrength;
            half3 worldN = normalize(half3(-slope.x+ripple.x,1,-slope.y+ripple.y));
            // Convert the authored world-up water frame into the mesh tangent
            // frame. Correct with rotated/repacked UVs and mirrored tangents.
            half3 T = normalize(WorldNormalVector(IN,half3(1,0,0)));
            half3 B = normalize(WorldNormalVector(IN,half3(0,1,0)));
            half3 N = normalize(WorldNormalVector(IN,half3(0,0,1)));
            o.Normal = normalize(half3(dot(worldN,T),dot(worldN,B),dot(worldN,N)));
            o.Albedo = tex2D(_MainTex,IN.uv_MainTex*.25).rgb*_Color.rgb;
            o.Smoothness = saturate(1-_Roughness);
            o.Metallic = saturate(_Metallic);
            o.Occlusion = 1;
            o.Alpha = 1;
        }
        ENDCG
    }
    FallBack "Standard"
}

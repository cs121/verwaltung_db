Shader "Custom/TeleportWithMotionVectors"
{
    Properties
    {
        _BaseColor ("Base Color", Color) = (0.2, 0.8, 1, 1)
        _InnerColor ("Inner Color", Color) = (0.85, 0.95, 1, 1)
        _DistortionStrength ("Distortion", Range(0, 2)) = 0.65
        _RimPower ("Rim Power", Range(0.1, 8)) = 2.5
        _NoiseSpeed ("Noise Speed", Range(0, 5)) = 1.6
        _NoiseScale ("Noise Scale", Range(0.5, 4)) = 1.2
    }

    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "Queue" = "Transparent" "RenderType" = "Transparent" }
        LOD 250
        Blend SrcAlpha OneMinusSrcAlpha
        Cull Off
        ZWrite Off

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseColor;
                float4 _InnerColor;
                float _DistortionStrength;
                float _RimPower;
                float _NoiseSpeed;
                float _NoiseScale;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS   : NORMAL;
                float2 uv         : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS   : TEXCOORD1;
                float2 uv         : TEXCOORD2;
                float fogCoord    : TEXCOORD3;
            };

            float Noise(float2 p)
            {
                float2 n = floor(p);
                float2 f = frac(p);
                f = f * f * (3.0 - 2.0 * f);
                float a = frac(sin(dot(n, float2(12.9898, 78.233))) * 43758.5453);
                float b = frac(sin(dot(n + float2(1, 0), float2(12.9898, 78.233))) * 43758.5453);
                float c = frac(sin(dot(n + float2(0, 1), float2(12.9898, 78.233))) * 43758.5453);
                float d = frac(sin(dot(n + float2(1, 1), float2(12.9898, 78.233))) * 43758.5453);
                return lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y);
            }

            Varyings vert(Attributes input)
            {
                Varyings output;
                VertexPositionInputs positionInputs = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = positionInputs.positionCS;
                output.positionWS = positionInputs.positionWS;
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                output.uv = input.uv;
                output.fogCoord = ComputeFogFactor(positionInputs.positionCS.z);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                float time = _Time.y * _NoiseSpeed;
                float2 radialUV = input.uv * _NoiseScale;

                float center = 1.0 - saturate(length(input.uv - 0.5) * 2.0);
                float rings = Noise(radialUV + time);
                float distortion = (rings - 0.5) * _DistortionStrength;

                float rim = pow(1.0 - saturate(dot(normalize(input.normalWS), normalize(_WorldSpaceCameraPos - input.positionWS))), _RimPower);
                float intensity = saturate(center * 0.8 + rim * 0.6 + distortion * 0.5);

                half4 color;
                color.rgb = lerp(_BaseColor.rgb, _InnerColor.rgb, intensity);
                color.a = saturate(intensity * 0.85 + 0.15);

                color.rgb = MixFog(color.rgb, input.fogCoord);
                return color;
            }
            ENDHLSL
        }

        Pass
        {
            Name "MotionVectors"
            Tags { "LightMode" = "MotionVectors" }

            HLSLPROGRAM
            #pragma vertex vertMotion
            #pragma fragment fragMotion

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/MotionVectors.hlsl"

            struct MotionAttributes
            {
                float4 positionOS : POSITION;
                float3 normalOS   : NORMAL;
                float4 tangentOS  : TANGENT;
            };

            struct MotionVaryings
            {
                float4 positionCS     : SV_POSITION;
                float4 prevPositionCS : TEXCOORD0;
            };

            MotionVaryings vertMotion(MotionAttributes input)
            {
                MotionVaryings output;
                VertexPositionInputs positionInputs = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = positionInputs.positionCS;
                output.prevPositionCS = TransformPreviousObjectToHClip(input.positionOS.xyz);
                return output;
            }

            float4 fragMotion(MotionVaryings input) : SV_Target
            {
                return PackMotionVector(input.positionCS, input.prevPositionCS);
            }
            ENDHLSL
        }
    }
    FallBack Off
}

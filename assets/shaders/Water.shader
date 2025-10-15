Shader "Custom/WaterWithMotionVectors"
{
    Properties
    {
        _DeepColor ("Deep Color", Color) = (0.0, 0.32, 0.45, 1)
        _ShallowColor ("Shallow Color", Color) = (0.18, 0.6, 0.78, 1)
        _FoamColor ("Foam Color", Color) = (0.9, 0.95, 1.0, 1)
        _WaveAmplitude ("Wave Amplitude", Range(0, 1)) = 0.15
        _WaveFrequency ("Wave Frequency", Range(0.1, 8)) = 2.5
        _WaveSpeed ("Wave Speed", Range(0, 4)) = 1.2
        _FoamThreshold ("Foam Threshold", Range(0, 1)) = 0.6
        _Smoothness ("Smoothness", Range(0, 1)) = 0.8
    }

    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "Queue" = "Transparent" "RenderType" = "Transparent" }
        LOD 300
        Blend SrcAlpha OneMinusSrcAlpha
        Cull Back
        ZWrite Off

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _ADDITIONAL_LIGHTS
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS
            #pragma multi_compile _ _SHADOWS_SOFT
            #pragma multi_compile_fog

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _DeepColor;
                float4 _ShallowColor;
                float4 _FoamColor;
                float _WaveAmplitude;
                float _WaveFrequency;
                float _WaveSpeed;
                float _FoamThreshold;
                float _Smoothness;
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

            float WaveNoise(float2 uv)
            {
                float2 n = floor(uv);
                float2 f = frac(uv);
                f = f * f * (3.0 - 2.0 * f);
                float a = frac(sin(dot(n, float2(127.1, 311.7))) * 43758.5453);
                float b = frac(sin(dot(n + float2(1, 0), float2(127.1, 311.7))) * 43758.5453);
                float c = frac(sin(dot(n + float2(0, 1), float2(127.1, 311.7))) * 43758.5453);
                float d = frac(sin(dot(n + float2(1, 1), float2(127.1, 311.7))) * 43758.5453);
                return lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y);
            }

            Varyings vert(Attributes input)
            {
                Varyings output;
                float time = _Time.y * _WaveSpeed;

                float wave = sin((input.uv.x + time) * _WaveFrequency) * _WaveAmplitude;
                input.positionOS.y += wave;
                input.normalOS = normalize(float3(-_WaveAmplitude * _WaveFrequency * cos((input.uv.x + time) * _WaveFrequency), 1.0, 0.0));

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
                float depthFactor = saturate(input.uv.y);
                float3 baseColor = lerp(_ShallowColor.rgb, _DeepColor.rgb, depthFactor);

                float time = _Time.y * _WaveSpeed;
                float foamNoise = WaveNoise(input.uv * _WaveFrequency + time);
                float foam = smoothstep(_FoamThreshold - 0.1, _FoamThreshold + 0.05, foamNoise);

                Light mainLight = GetMainLight();
                float3 normalWS = normalize(input.normalWS);
                float3 viewDirWS = SafeNormalize(_WorldSpaceCameraPos - input.positionWS);
                float3 halfDir = SafeNormalize(mainLight.direction + viewDirWS);

                float ndotl = saturate(dot(normalWS, mainLight.direction));
                float fresnel = pow(1.0 - saturate(dot(normalWS, viewDirWS)), 3.0);
                float specular = pow(saturate(dot(normalWS, halfDir)), 32.0) * _Smoothness;

                float3 lighting = baseColor * (ndotl + 0.15) + fresnel * 0.25;
                float3 foamColor = _FoamColor.rgb * foam;

                half4 color;
                color.rgb = lighting + foamColor + specular * 0.25;
                color.a = saturate(0.75 + fresnel * 0.25);

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
                float2 uv         : TEXCOORD0;
            };

            struct MotionVaryings
            {
                float4 positionCS     : SV_POSITION;
                float4 prevPositionCS : TEXCOORD0;
            };

            MotionVaryings vertMotion(MotionAttributes input)
            {
                MotionVaryings output;
                float time = _Time.y * _WaveSpeed;
                float wave = sin((input.uv.x + time) * _WaveFrequency) * _WaveAmplitude;
                float3 positionOS = input.positionOS.xyz;
                positionOS.y += wave;

                VertexPositionInputs positionInputs = GetVertexPositionInputs(positionOS);
                output.positionCS = positionInputs.positionCS;
                output.prevPositionCS = TransformPreviousObjectToHClip(positionOS);
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

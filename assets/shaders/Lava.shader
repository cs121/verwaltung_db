Shader "Custom/LavaWithMotionVectors"
{
    Properties
    {
        _BaseColor ("Base Color", Color) = (1, 0.35, 0.1, 1)
        _EmissionColor ("Emission Color", Color) = (1.5, 0.65, 0.25, 1)
        _DistortionStrength ("Distortion", Range(0, 1)) = 0.35
        _FlowSpeed ("Flow Speed", Range(0, 2)) = 0.75
        _Tiling ("Tiling", Vector) = (1, 1, 0, 0)
    }

    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "Queue" = "Transparent" "RenderType" = "Transparent" }
        LOD 300
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
            #pragma multi_compile _ _ADDITIONAL_LIGHTS
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS
            #pragma multi_compile _ _SHADOWS_SOFT
            #pragma multi_compile _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fog

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseColor;
                float4 _EmissionColor;
                float4 _Tiling;
                float _DistortionStrength;
                float _FlowSpeed;
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

            float2 FlowUV(float2 baseUV, float time, float2 tiling)
            {
                float2 flow = baseUV * tiling;
                flow += float2(time * _FlowSpeed, -time * 0.25 * _FlowSpeed);
                return flow;
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
                float time = _Time.y;
                float2 tiling = _Tiling.xy;

                float2 flowA = FlowUV(input.uv, time, tiling);
                float2 flowB = FlowUV(input.uv, time + 1.3, tiling);

                float noiseA = frac(sin(dot(flowA, float2(12.9898, 78.233))) * 43758.5453);
                float noiseB = frac(sin(dot(flowB, float2(39.3468, 11.135))) * 24634.6345);
                float combined = saturate(noiseA * 0.6 + noiseB * 0.4);

                float emissivePulse = pow(combined, 3.0);
                float alpha = saturate(combined + 0.35);

                float3 normalWS = normalize(input.normalWS);
                float3 viewDirWS = SafeNormalize(_WorldSpaceCameraPos - input.positionWS);
                float3 lightDirWS = normalize(GetMainLight().direction);
                float3 halfDir = SafeNormalize(lightDirWS + viewDirWS);

                float ndotl = saturate(dot(normalWS, lightDirWS));
                float specular = pow(saturate(dot(normalWS, halfDir)), 24.0);

                float3 baseColor = _BaseColor.rgb * (0.35 + 0.65 * combined);
                float3 lighting = baseColor * ndotl + 0.1 * baseColor;
                float3 emission = _EmissionColor.rgb * (emissivePulse + specular * 0.15);

                half4 color;
                color.rgb = lighting + emission;
                color.a = alpha;

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
                float4 positionCS    : SV_POSITION;
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

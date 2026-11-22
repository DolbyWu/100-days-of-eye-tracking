void main() {
    vec4 uGaze = texelFetch(sTD2DInputs[2],ivec2(0,0),0);
    vec4 uMotion = texelFetch(sTD2DInputs[2],ivec2(1,0),0);
    vec4 uWave = texelFetch(sTD2DInputs[2],ivec2(2,0),0);
    vec4 uStyle = texelFetch(sTD2DInputs[2],ivec2(3,0),0);
    ivec2 i = ivec2(vUV.st*vec2(textureSize(sTD2DInputs[0],0)));
    float dt = uMotion.w;
    vec2 v = cell(sTD2DInputs[1],i).xy;
    float ink = sampleGrid(sTD2DInputs[0],vec2(i)-dt*v).r*exp(-uStyle.w*dt);
    vec2 r = fract(vUV.st-uGaze.xy+.5)-.5;
    float s = length(r)/max(uGaze.w,.001);
    float strands = .5+.5*sin(36.0*s+4.0*sin(atan(r.y,r.x+.00001)*5.0));
    ink += dt*uGaze.z*exp(-2.5*s*s)*(1.9+4.2*pow(strands,5.0));
    vec2 d = fract(vUV.st-uWave.xy+.5)-.5;
    ink += 3.0*dt*uWave.w*exp(-pow((length(d)-(.016+.42*uWave.z))/.008,2.0));
    emit(vec4(clamp(ink,0.0,7.0),0,0,1));
}

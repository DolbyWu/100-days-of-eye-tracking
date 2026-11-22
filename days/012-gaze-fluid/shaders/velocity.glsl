void main() {
    vec4 uGaze = texelFetch(sTD2DInputs[1],ivec2(0,0),0);
    vec4 uMotion = texelFetch(sTD2DInputs[1],ivec2(1,0),0);
    vec4 uWave = texelFetch(sTD2DInputs[1],ivec2(2,0),0);
    vec4 uStyle = texelFetch(sTD2DInputs[1],ivec2(3,0),0);
    ivec2 i = ivec2(vUV.st*vec2(textureSize(sTD2DInputs[0],0)));
    float dt = uMotion.w;
    vec2 previous = cell(sTD2DInputs[0],i).xy;
    vec2 v = sampleGrid(sTD2DInputs[0],vec2(i)-dt*previous).xy * exp(-dt*uStyle.z);
    vec2 r = fract(vUV.st-uGaze.xy+.5)-.5;
    float w = exp(-dot(r,r)/(2.0*max(.0001,uGaze.w*uGaze.w)));
    float speed = min(length(uMotion.xy),3.0);
    vec2 tangent = vec2(-r.y,r.x)/max(uGaze.w,.001);
    vec2 turbulence = vec2(sin(r.y*280.0),sin(r.x*245.0));
    v += dt*uGaze.z*w*(uStyle.x*clamp(uMotion.xy,vec2(-3),vec2(3)) +
        uStyle.y*(.25+min(uMotion.z,2.0))*tangent + 90.0*speed*turbulence);
    vec2 d = fract(vUV.st-uWave.xy+.5)-.5;
    float dist = length(d);
    float ring = exp(-pow((dist-(.016+.42*uWave.z))/.023,2.0));
    v += dt*uWave.w*ring*(d/max(dist,.001))*500.0*(.7+.3*sin(atan(d.y,d.x+.00001)*9.0));
    emit(vec4(clamp(v,vec2(-350),vec2(350)),0,1));
}

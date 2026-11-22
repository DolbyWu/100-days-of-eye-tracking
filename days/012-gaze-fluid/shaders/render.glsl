// Integrate a fine grain along the projected velocity field.
float grain(vec2 p) {
    vec2 i = floor(p);
    vec2 f = smoothstep(vec2(0), vec2(1), fract(p));
    vec4 n = fract(sin(vec4(dot(i, vec2(127.1,311.7))) +
                       vec4(0,127.1,311.7,438.8))*43758.5453);
    return mix(mix(n.x,n.y,f.x),mix(n.z,n.w,f.x),f.y);
}
vec2 flow(vec2 p) {
    vec2 v = sampleGrid(sTD2DInputs[1],p).xy;
    return v / max(length(v), 1.0);
}

void main() {
    vec2 index = vUV.st*vec2(textureSize(sTD2DInputs[0],0))-.5;
    float dye = sampleGrid(sTD2DInputs[0],index).r;
    vec2 gradient = vec2(sampleGrid(sTD2DInputs[0],index+vec2(1,0)).r-dye,
                         sampleGrid(sTD2DInputs[0],index+vec2(0,1)).r-dye);
    float body = 1.0-exp(-dye*2.1);
    float edge = 1.0-exp(-length(gradient)*15.0);
    vec2 a = index, b = index;
    float streak = grain(index*2.5)*2.0;
    for (int j=0; j<7; ++j) {
        a += flow(a)*1.55;
        b -= flow(b)*1.55;
        streak += grain(a*2.5)+grain(b*2.5);
    }
    streak = pow(smoothstep(.29,.68,streak/16.0), 2.1);
    float light = max(body*.3,edge)*(.25+1.5*streak);
    float filament = min(1.0, body*streak*1.8);
    vec3 cyan = vec3(.012,.82,.92)*(light+filament*.55);
    vec3 white = vec3(.76,.95,1.0)*pow(min(1.0,light+filament*.68),3.2);
    emit(vec4(clamp(cyan+white,0.0,1.0),1));
}

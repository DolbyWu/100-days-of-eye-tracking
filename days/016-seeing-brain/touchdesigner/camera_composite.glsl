out vec4 fragColor;
void main(){
    vec2 uv=vUV.st;
    vec3 camera=texture(sTD2DInputs[2],vec2(1.-uv.x,uv.y)).rgb;
    vec3 scan=texture(sTD2DInputs[0],uv).rgb;
    float peak=max(scan.r,max(scan.g,scan.b));
    float coverage=smoothstep(.003,.38,peak)*.86;
    vec3 scene=camera*(1.-coverage)+scan;
    vec4 marks=texture(sTD2DInputs[1],uv);
    fragColor=TDOutputSwizzle(vec4(mix(scene,marks.rgb,marks.a),1.));
}

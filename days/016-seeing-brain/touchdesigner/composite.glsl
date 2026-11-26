out vec4 fragColor;
uniform vec4 levels;
uniform vec4 optics;
void main(){
    vec2 uv=vUV.st;
    vec3 skull=texture(sTD2DInputs[0],uv).rgb;
    vec3 brain=texture(sTD2DInputs[1],uv).rgb;
    vec3 nodes=texture(sTD2DInputs[2],uv).rgb;
    vec3 tissue=mix(brain*levels.y,skull,levels.x*sqrt(clamp(skull.b,0.,1.)));
    vec3 glow=vec3(0.);
    vec2 px=uTD2DInfos[2].res.xy*3.;
    for(int i=0;i<8;i++){
        float a=float(i)*.785398;
        glow+=texture(sTD2DInputs[2],uv+px*vec2(cos(a),sin(a))).rgb;
    }
    vec3 light=tissue*(1.+.15*levels.w)+nodes+glow*(.125*optics.x);
    fragColor=TDOutputSwizzle(vec4(1.-exp(-light*levels.z),1.));
}

out vec4 fragColor;
void main(){
    vec2 uv=vUV.st;
    vec3 portrait=texture(sTD2DInputs[0],uv).rgb;
    vec4 ink=texture(sTD2DInputs[1],uv);
    fragColor=TDOutputSwizzle(vec4(ink.rgb+(1.-ink.a)*portrait,1.));
}

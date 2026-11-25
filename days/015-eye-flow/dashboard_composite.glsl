out vec4 fragColor;
void main(){
    vec2 uv=vUV.st;
    vec3 color=texture(sTD2DInputs[0],uv).rgb;
    vec2 cardUV=(uv*vec2(1280.,720.)-vec2(16.,16.))/vec2(1248.,154.);
    if(all(greaterThanEqual(cardUV,vec2(0.))) && all(lessThan(cardUV,vec2(1.)))){
        vec4 card=texture(sTD2DInputs[1],cardUV);
        color=mix(color,card.rgb,card.a);
    }
    fragColor=TDOutputSwizzle(vec4(color,1.));
}

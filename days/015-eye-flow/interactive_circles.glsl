out vec4 fragColor;
void main(){
    vec2 uv=vUV.st;
    vec4 mode=texelFetch(sTD2DInputs[2],ivec2(2,0),0);
    vec3 color=mode.y>.5 ? texture(sTD2DInputs[0],vec2(1.-uv.x,uv.y)).rgb
                         : mix(vec3(.026,.043,.06),vec3(.09,.14,.17),uv.y);
    for(int i=0;i<2;++i){
        vec4 eye=texelFetch(sTD2DInputs[2],ivec2(i,0),0);
        vec2 q=(uv*vec2(16./9.,1.)-eye.xy)/max(.001,eye.z);
        float edge=length(q);
        if(edge>1.)continue;
        vec2 sampleUV=clamp(vec2(.5,.61)+q*.37,.01,.99);
        vec3 iris=mix(vec3(.09,.32,.31),vec3(.82,.86,.81),smoothstep(.34,.36,edge));
        iris=mix(vec3(.008,.018,.025),iris,smoothstep(.14,.16,edge));
        if(mode.z>.5 && textureSize(sTD2DInputs[1],0).x>128)
            iris=texture(sTD2DInputs[1],vec2((float(i)+sampleUV.x)*.5,sampleUV.y)).rgb;
        color=mix(color,iris,1.-smoothstep(.985,1.,edge));
    }
    fragColor=TDOutputSwizzle(vec4(color,1.));
}

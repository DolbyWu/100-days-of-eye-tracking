out vec4 fragColor;
const float ratio=16./9.;
const float radius=.096;
float segment(vec2 p,vec2 a,vec2 b){
    vec2 d=b-a;
    return length(p-a-d*clamp(dot(p-a,d)/max(dot(d,d),1e-7),0.,1.));
}
void main(){
    vec2 uv=vUV.st;
    vec2 p=uv*vec2(ratio,1.);
    vec4 settings=texelFetch(sTD2DInputs[2],ivec2(2,0),0);
    vec2 base=vec2(settings.z>.5?1.-uv.x:uv.x,uv.y);
    vec3 color=settings.w>.5?texture(sTD2DInputs[0],base).rgb:
        mix(vec3(.035,.055,.075),vec3(.10,.16,.20),uv.y);
    for(int i=0;i<46;++i){
        if(i>=int(settings.x)) break;
        vec4 bone=texelFetch(sTD2DInputs[2],ivec2(i+3,0),0);
        float d=segment(p,bone.xy,bone.zw);
        color=mix(color,vec3(.52,1.,.92),.8*(1.-smoothstep(.0012,.0035,d)));
    }
    for(int i=0;i<2;++i){
        vec4 ball=texelFetch(sTD2DInputs[2],ivec2(i,0),0);
        vec2 q=(p-ball.xy)/radius;
        // Symmetric, area-preserving stretch keeps both eyes facing front.
        vec2 strain=clamp(ball.zw,vec2(-.16),vec2(.16));
        q=(q-vec2(strain.x*q.x+strain.y*q.y,strain.y*q.x-strain.x*q.y))
            * inversesqrt(1.-dot(strain,strain));
        float rr=dot(q,q);
        color*=1.-.30*exp(-2.1*dot(q+vec2(-.14,.22),q+vec2(-.14,.22)));
        if(rr>=1.) continue;
        vec2 uvEye=q*.5+.5;
        vec3 iris=vec3(.80,.85,.84);
        float d=length((uvEye-.5)*vec2(1.,.67));
        iris=mix(vec3(.08,.44,.45),iris,smoothstep(.088,.097,d));
        iris=mix(vec3(.005,.013,.016),iris,smoothstep(.045,.050,d));
        vec2 crop=vec2(.5,.61)+q*.37;
        vec2 source=vec2((float(i)+clamp(crop.x,.01,.99))*.5,clamp(crop.y,0.,1.));
        if(settings.y<.5 && textureSize(sTD2DInputs[1],0).x>64)
            iris=texture(sTD2DInputs[1],source).rgb;
        color=mix(color,iris,1.-smoothstep(.974,1.,rr));
    }
    fragColor=TDOutputSwizzle(vec4(color,1.));
}

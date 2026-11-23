// Procedural synapses, filaments and gaze driven particles. Inputs: fluid, unused art, gaze parameters.
out vec4 fragColor;
float hash12(vec2 p) { return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
vec2 site(vec2 id) { return (id + vec2(.5) + .27*(vec2(hash12(id),hash12(id+71.7))-.5))/vec2(7.0,5.0); }
float segment(vec2 p,vec2 a,vec2 b) {
    vec2 v=b-a;
    return length(p-a-v*clamp(dot(p-a,v)/max(dot(v,v),1e-5),0.0,1.0));
}
void main() {
    vec2 uv=vUV.st;
    vec2 p=uv*vec2(1.47,1.0);
    vec4 gaze=texelFetch(sTD2DInputs[2],ivec2(0,0),0);
    vec4 motion=texelFetch(sTD2DInputs[2],ivec2(1,0),0);
    vec3 flow=texture(sTD2DInputs[0],uv).rgb;
    float residue=max(flow.g,flow.b);
    float line=0.0, nodes=0.0, particles=0.0, reaction=0.0;
    vec2 cell=floor(uv*vec2(7.0,5.0));
    for(int j=-1;j<=1;j++) for(int i=-1;i<=1;i++) {
        vec2 id=cell+vec2(float(i),float(j));
        if(any(lessThan(id,vec2(0.0))) || any(greaterThanEqual(id,vec2(7.0,5.0)))) continue;
        vec2 a=site(id)*vec2(1.47,1.0);
        float dist=length(p-a);
        float attention=gaze.z*(1.0-smoothstep(.02,.19,length((uv-gaze.xy)*vec2(1.47,1.0))));
        float activation=attention*(.35+.65*smoothstep(0.0,1.2,motion.z));
        nodes=max(nodes,(1.0-smoothstep(.012,.030,dist))*(.26+activation));
        reaction=max(reaction,activation*(1.0-smoothstep(.018,.080,dist)));
        for(int k=0;k<2;k++) {
            vec2 next=id+(k==0?vec2(1,0):vec2(0,1));
            if(any(greaterThanEqual(next,vec2(7.0,5.0)))) continue;
            vec2 b=site(next)*vec2(1.47,1.0);
            float d=segment(p,a,b);
            float spark=exp(-72.0*length(p-mix(a,b,fract(hash12(id+float(k)*17.0)+residue*.8))));
            line=max(line,(1.0-smoothstep(.0015,.0045,d))*(.12+.5*residue));
            particles=max(particles,spark*(.12+.85*residue+.4*attention));
        }
    }
    vec3 c=vec3(.015,.028,.044);
    c+=vec3(.06,.52,.65)*line+vec3(.15,.76,.88)*nodes;
    c+=vec3(.45,.94,1.0)*particles;
    c+=vec3(.98,.24,.52)*reaction;
    c+=vec3(.03,.54,.8)*pow(residue,.8)*.55;
    fragColor=TDOutputSwizzle(vec4(clamp(c,0.0,1.0),1.0));
}

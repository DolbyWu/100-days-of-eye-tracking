// Inputs: procedural neural art, Neon binocular eye RTSP, live gaze parameter texture.
out vec4 fragColor;
float lineMask(vec2 p, vec2 a, vec2 b, float w) {
    vec2 v=b-a;
    float t=clamp(dot(p-a,v)/max(dot(v,v),.01),0.0,1.0);
    return 1.0-smoothstep(w,w+1.2,length(p-a-t*v));
}
float boxMask(vec2 p,vec2 c,vec2 radius) {
    vec2 d=abs(p-c)-radius;
    return 1.0-smoothstep(.6,1.8,abs(max(d.x,d.y)));
}
void main() {
    vec2 uv=vUV.st;
    vec2 canvas=vec2(textureSize(sTD2DInputs[0],0));
    vec2 source=max(vec2(textureSize(sTD2DInputs[1],0)),vec2(1));
    vec2 p=uv*canvas;
    vec2 hi=canvas-vec2(22.0);
    vec2 size=vec2(min(320.0,canvas.x*.265),0.0);
    size.y=min(size.x*source.y/source.x,canvas.y*.32);
    vec2 lo=hi-size;
    vec3 color=texture(sTD2DInputs[0],uv).rgb;
    vec4 gaze=texelFetch(sTD2DInputs[2],ivec2(0,0),0);
    vec2 anchor=lo+vec2(size.x*.5,size.y*.5);
    if(gaze.z>.5) {
        vec2 point=clamp(gaze.xy*canvas,vec2(17),canvas-17.0);
        float wire=lineMask(p,anchor,point,.60);
        float dotSize=length(p-point);
        float dotMask=1.0-smoothstep(2.0,3.6,dotSize);
        float frame=boxMask(p,point,vec2(9));
        color+=vec3(.44,.88,1.0)*(wire*.8+dotMask+frame*.85+exp(-dotSize*.13)*.25);
    }
    if(all(greaterThanEqual(p,lo-2.0)) && all(lessThanEqual(p,hi+2.0))) {
        vec2 q=(p-lo)/size;
        if(all(greaterThanEqual(q,vec2(0))) && all(lessThanEqual(q,vec2(1)))) {
            vec2 d=1.0/source;
            vec3 center=texture(sTD2DInputs[1],q).rgb;
            vec3 around=.25*(texture(sTD2DInputs[1],clamp(q+vec2(d.x,0),0.0,1.0)).rgb
                              +texture(sTD2DInputs[1],clamp(q-vec2(d.x,0),0.0,1.0)).rgb
                              +texture(sTD2DInputs[1],clamp(q+vec2(0,d.y),0.0,1.0)).rgb
                              +texture(sTD2DInputs[1],clamp(q-vec2(0,d.y),0.0,1.0)).rgb);
            color=clamp((center-.5)*1.12+.5+.55*(center-around),0.0,1.0);
            // Optical candidate search in each camera half. Confidence is based on local contrast.
            if(source.x>32.0 && source.y>32.0) {
                for(int eye=0;eye<2;eye++) {
                    float darkest=2.0,brightest=-1.0;
                    vec2 pupil=vec2(.25+.5*float(eye),.5);
                    vec2 glint=pupil;
                    float base=.5*float(eye);
                    for(int iy=0;iy<7;iy++) for(int ix=0;ix<7;ix++) {
                        vec2 candidate=vec2(base+.5*(.16+.68*(float(ix)+.5)/7.0),
                                            .18+.64*(float(iy)+.5)/7.0);
                        vec3 rgb=texture(sTD2DInputs[1],candidate).rgb;
                        float lum=dot(rgb,vec3(.2126,.7152,.0722));
                        if(lum<darkest) { darkest=lum; pupil=candidate; }
                        if(lum>brightest) { brightest=lum; glint=candidate; }
                    }
                    float confidence=smoothstep(.10,.28,brightest-darkest);
                    vec2 pupilP=lo+pupil*size;
                    vec2 glintP=lo+glint*size;
                    float pupilBox=boxMask(p,pupilP,vec2(8));
                    float glintBox=boxMask(p,glintP,vec2(5));
                    float direction=lineMask(p,lo+vec2(base+.25,.5)*size,pupilP,.45);
                    color+=confidence*(vec3(1.0,.19,.30)*pupilBox
                                       +vec3(.68,.92,1.0)*(.55*glintBox+.7*direction));
                }
            }
        } else color=vec3(.35,.61,.68);
    }
    fragColor=TDOutputSwizzle(vec4(clamp(color,0.0,1.0),1.0));
}

// Inputs: neural art, Neon eye RTSP, gaze params, eye detections, AprilTag overlay.
out vec4 fragColor;
float lineAt(vec2 p,vec2 a,vec2 b,float w){vec2 v=b-a;float t=clamp(dot(p-a,v)/max(dot(v,v),.001),0.,1.);return 1.-smoothstep(w,w+1.,length(p-a-t*v));}
float ringAt(vec2 p,vec2 c,float r,float w){return 1.-smoothstep(w,w+1.2,abs(length(p-c)-r));}
float boxAt(vec2 p,vec2 c,vec2 r,float w){vec2 d=abs(p-c)-r;return 1.-smoothstep(w,w+1.2,abs(max(d.x,d.y)));}
int maskDigit(int d){int m[10]=int[10](63,6,91,79,102,109,125,7,127,111);return m[clamp(d,0,9)];}
float digitAt(vec2 p,int d){
    if(p.x< -2.||p.x>8.||p.y< -2.||p.y>13.)return 0.;
    int m=maskDigit(d);float v=0.;
    if((m&1)!=0)v=max(v,lineAt(p,vec2(1,11),vec2(6,11),.55));
    if((m&2)!=0)v=max(v,lineAt(p,vec2(6,10),vec2(6,6),.55));
    if((m&4)!=0)v=max(v,lineAt(p,vec2(6,5),vec2(6,1),.55));
    if((m&8)!=0)v=max(v,lineAt(p,vec2(1,0),vec2(6,0),.55));
    if((m&16)!=0)v=max(v,lineAt(p,vec2(0,5),vec2(0,1),.55));
    if((m&32)!=0)v=max(v,lineAt(p,vec2(0,10),vec2(0,6),.55));
    if((m&64)!=0)v=max(v,lineAt(p,vec2(1,5.5),vec2(6,5.5),.55));
    return v;
}
float mmAt(vec2 p,float mm){
    if(mm<0.)return 0.;
    int n=int(clamp(mm,0.,9.99)*100.+.5);
    float v=digitAt(p,n/100);
    v=max(v,1.-smoothstep(.5,1.4,length(p-vec2(9,0))));
    v=max(v,digitAt(p-vec2(13,0),(n/10)%10));
    v=max(v,digitAt(p-vec2(22,0),n%10));
    return v;
}
// Draw the four AprilTags from the same 8x8 bits as surface-markers.png.
// This keeps calibration visible even if Movie File In drops PNG alpha.
vec4 surfaceTag(vec2 uv){
    vec2 q=vec2(uv.x,1.-uv.y)*vec2(1200.,815.);
    ivec2 origin[4]=ivec2[4](ivec2(20,20),ivec2(1068,20),ivec2(1068,683),ivec2(20,683));
    int rows[32]=int[32](
        0,8,44,80,48,58,106,0,
        0,18,90,48,120,46,108,0,
        0,28,8,18,64,36,110,0,
        0,48,100,82,78,14,114,0);
    for(int id=0;id<4;id++){
        vec2 local=q-vec2(origin[id]);
        if(all(greaterThanEqual(local,vec2(0.)))&&all(lessThan(local,vec2(112.)))){
            ivec2 cell=ivec2(floor((local-12.)/11.));
            if(any(lessThan(cell,ivec2(0)))||any(greaterThan(cell,ivec2(7))))
                return vec4(1.);
            int white=(rows[id*8+cell.y]>>cell.x)&1;
            return vec4(vec3(float(white)),1.);
        }
    }
    return vec4(0.);
}
void main(){
    const vec3 cyan=vec3(.04,1.,1.);
    vec2 uv=vUV.st;
    vec2 canvas=vec2(textureSize(sTD2DInputs[0],0));
    vec2 src=max(vec2(textureSize(sTD2DInputs[1],0)),vec2(1.));
    vec2 p=uv*canvas;
    vec2 size=vec2(min(320.,canvas.x*.265),0.);
    size.y=min(size.x*src.y/src.x,canvas.y*.32);
    vec2 hi=vec2((canvas.x+size.x)*.5,canvas.y-22.);
    vec2 lo=hi-size;
    vec3 color=texture(sTD2DInputs[0],uv).rgb;
    vec4 gaze=texelFetch(sTD2DInputs[2],ivec2(0,0),0);
    vec4 left=texelFetch(sTD2DInputs[3],ivec2(0,0),0);
    vec4 right=texelFetch(sTD2DInputs[3],ivec2(1,0),0);
    vec4 metric=texelFetch(sTD2DInputs[3],ivec2(5,0),0);
    vec4 changes=texelFetch(sTD2DInputs[3],ivec2(6,0),0);
    vec2 anchor=lo+size*.5;
    if(left.w>.5)anchor=lo+vec2(left.x,1.-left.y)*size;
    if(right.w>.5)anchor=left.w>.5 ? .5*(anchor+lo+vec2(right.x,1.-right.y)*size) : lo+vec2(right.x,1.-right.y)*size;
    if(gaze.z>.5){
        vec2 target=clamp(gaze.xy*canvas,vec2(16.),canvas-16.);
        float d=length(p-target);
        float ink=.94*lineAt(p,anchor,target,.35)+ringAt(p,target,8.,.45)
                   +(1.-smoothstep(2.,3.2,d))+.15*exp(-.13*d);
        color=mix(color,cyan,clamp(ink,0.,1.));
    }
    if(all(greaterThanEqual(p,lo-2.))&&all(lessThanEqual(p,hi+2.))){
        vec2 q=(p-lo)/size;
        if(all(greaterThanEqual(q,vec2(0.)))&&all(lessThanEqual(q,vec2(1.)))){
            vec2 texel=1./src;
            vec3 center=texture(sTD2DInputs[1],q).rgb;
            vec3 nearby=.25*(texture(sTD2DInputs[1],clamp(q+vec2(texel.x,0),0.,1.)).rgb
                              +texture(sTD2DInputs[1],clamp(q-vec2(texel.x,0),0.,1.)).rgb
                              +texture(sTD2DInputs[1],clamp(q+vec2(0,texel.y),0.,1.)).rgb
                              +texture(sTD2DInputs[1],clamp(q-vec2(0,texel.y),0.,1.)).rgb);
            color=clamp((center-.5)*1.12+.5+.52*(center-nearby),0.,1.);
            for(int i=0;i<2;i++){
                vec4 eye=i==0?left:right;
                if(eye.w<.5)continue;
                vec2 c=lo+vec2(eye.x,1.-eye.y)*size;
                float radius=clamp(eye.z*size.x,8.,28.);
                float box=boxAt(p,c,vec2(radius+5.),.35);
                color=mix(color,cyan,box);
                float mm=i==0?metric.x:metric.y;
                vec2 label=lo+vec2(i==0?16.:size.x*.55,10.);
                color=mix(color,cyan,mmAt(p-label,mm));
            }
            for(int i=0;i<3;i++){
                vec4 change=texelFetch(sTD2DInputs[3],ivec2(i+2,0),0);
                if(change.z<=0.)continue;
                vec2 c=lo+vec2(change.x,1.-change.y)*size;
                vec2 r=max(change.zw*size*.5,vec2(5.));
                float strength=i==0?changes.x:(i==1?changes.y:changes.z);
                float box=boxAt(p,c,r,.8);
                float lead=lineAt(p,anchor,c,.35);
                color=mix(color,cyan,clamp(box*(.78+.22*strength)+.64*lead,0.,1.));
                int pct=int(clamp(strength*100.,0.,99.));
                vec2 label=p-(c+vec2(r.x+4.,0.));
                color=mix(color,cyan,max(digitAt(label,pct/10),digitAt(label-vec2(8.,0.),pct%10)));
            }
        } else color=cyan;
    }
    fragColor=TDOutputSwizzle(vec4(clamp(color,0.,1.),1.));
}

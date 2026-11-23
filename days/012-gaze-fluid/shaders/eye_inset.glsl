// Inputs: neural artwork, binocular IR image, live gaze parameter texture.
out vec4 fragColor;

float lineMask(vec2 p, vec2 a, vec2 b, float width) {
    vec2 ab = b-a;
    float t = clamp(dot(p-a,ab)/max(dot(ab,ab),.01),0.0,1.0);
    return 1.0-smoothstep(width,width+1.2,length(p-a-t*ab));
}

void main() {
    vec2 uv = vUV.st;
    vec2 canvas = vec2(textureSize(sTD2DInputs[0],0));
    vec2 source = vec2(textureSize(sTD2DInputs[1],0));
    vec2 p = uv*canvas;
    vec2 hi = canvas-vec2(22.0);
    vec2 size = vec2(min(320.0,canvas.x*.265),0.0);
    size.y = size.x*source.y/source.x;
    vec2 lo = hi-size;
    vec3 color = texture(sTD2DInputs[0],uv).rgb;

    vec4 gaze = texelFetch(sTD2DInputs[2],ivec2(0,0),0);
    if (gaze.z > .5) {
        vec2 point = clamp(gaze.xy*canvas,vec2(17),canvas-17.0);
        vec2 anchor = lo+vec2(0.0,size.y*.23);
        float wire = lineMask(p,anchor,point,.50);
        float dotSize = length(p-point);
        float dotMask = 1.0-smoothstep(2.1,3.3,dotSize);
        float box = max(abs(p.x-point.x),abs(p.y-point.y));
        float frame = 1.0-smoothstep(.55,1.65,abs(box-10.0));
        vec2 across = abs(p-point);
        float corners = smoothstep(4.2,5.3,min(across.x,across.y));
        float glow = exp(-dotSize*.14)*.34;
        color += vec3(.49,.84,1.0)*(wire*.65+dotMask+frame*corners*.86+glow);
    }
    if (all(greaterThanEqual(p,lo-2.0)) && all(lessThanEqual(p,hi+2.0))) {
        vec2 q = (p-lo)/size;
        if (all(greaterThanEqual(q,vec2(0))) && all(lessThanEqual(q,vec2(1)))) {
            vec2 d = 1.0/source;
            vec3 center = texture(sTD2DInputs[1],q).rgb;
            vec3 around = .25*(texture(sTD2DInputs[1],clamp(q+vec2(d.x,0),0.0,1.0)).rgb
                             + texture(sTD2DInputs[1],clamp(q-vec2(d.x,0),0.0,1.0)).rgb
                             + texture(sTD2DInputs[1],clamp(q+vec2(0,d.y),0.0,1.0)).rgb
                             + texture(sTD2DInputs[1],clamp(q-vec2(0,d.y),0.0,1.0)).rgb);
            color = (center-.5)*1.10+.5+.52*(center-around);
        } else {
            color = vec3(.37,.63,.70);
        }
    }
    fragColor = TDOutputSwizzle(vec4(clamp(color,0.0,1.0),1.0));
}

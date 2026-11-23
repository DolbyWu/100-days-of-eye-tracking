// Composite the reference, the animated relief points and the telemetry.
out vec4 fragColor;

float hash(vec2 v) {
    return fract(sin(dot(v,vec2(127.1,311.7)))*43758.5453);
}

void main() {
    vec2 uv = vUV.st;
    ivec2 size = textureSize(sTD2DInputs[0],0);
    vec2 aspect = vec2(float(size.x)/float(size.y),1.);
    vec3 controls = texelFetch(sTD2DInputs[0],ivec2(0,0),0).rgb;
    vec4 watch = texelFetch(sTD2DInputs[0],ivec2(1,0),0);
    ivec2 pixel = clamp(ivec2(uv*vec2(size)),ivec2(0),size-1);
    vec4 dots = pixel.y == 0 ? vec4(0.,0.,0.,1.) : texelFetch(sTD2DInputs[0],pixel,0);
    float delta = (controls.r*255.-128.)/63.5;
    float breath = (controls.g*255.-128.)/127.;
    float burst = controls.b;
    vec2 cells[4] = vec2[4](vec2(.219,.665),vec2(.61,.76),vec2(.843,.30),vec2(.342,.139));
    vec2 shift = vec2(0.);
    for(int i=0;i<4;++i) {
        vec2 d = uv-cells[i];
        shift += d*exp(-dot(d*aspect,d*aspect)*46.);
    }
    float pupil = sign(delta)*max(0.,abs(delta)-.045);
    vec2 from = clamp(uv-shift*(pupil*.055+breath*.070),0.,1.);
    vec3 photo = texture(sTD2DInputs[1],from).rgb;
    float gazeDistance = length((uv-watch.xy)*aspect);
    float local = watch.z*(1.-smoothstep(.012,.095,gazeDistance));
    float erase = local > 0. ? step(hash(floor(uv*vec2(size)*.43)),local*.75) : 0.;
    vec3 color = photo*(1.-.77*erase)*(1.-burst)+dots.rgb*mix(1.35,1.,burst);
    // Tint the source tissue even where the white fibers are already saturated.
    float focus = watch.a*(1.-smoothstep(.025,.103,gazeDistance))*(1.-erase*.7)*(1.-burst);
    float luminance = dot(photo,vec3(.2126,.7152,.0722));
    float tissue = smoothstep(.12,.49,luminance);
    float pink = smoothstep(.085,.30,photo.r-photo.g);
    float surface = max(tissue,pink);
    vec3 cyan = vec3(.04,1.,1.)*mix(.58,1.,tissue);
    color = mix(clamp(color,0.,1.),cyan,focus*surface*.96);
    if(dots.a < .08) {
        color = dots.rgb;
    } else {
        float pulse = clamp((1.-dots.a)*(255./222.),0.,1.);
        color = mix(clamp(color,0.,1.),vec3(1.),pulse*surface);
    }
    fragColor = TDOutputSwizzle(vec4(clamp(color,0.,1.),1.));
}

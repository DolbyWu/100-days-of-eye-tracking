// Fluid, artwork, live parameter texels. Pink marks are interaction targets.
float pinkMask(vec3 rgb) {
    return smoothstep(.08, .21, rgb.r - rgb.g)
         * smoothstep(.25, .57, rgb.r);
}
float hashPoint(vec2 p) { return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }

void main() {
    vec2 uv = vUV.st;
    vec4 gaze = texelFetch(sTD2DInputs[2], ivec2(0,0), 0);
    vec4 motion = texelFetch(sTD2DInputs[2], ivec2(1,0), 0);
    vec4 wave = texelFetch(sTD2DInputs[2], ivec2(2,0), 0);
    // Radius follows pupil change in the bridge; expand the image subtly.
    float breathe = clamp((gaze.w-.038)*2.2,-.04,.08);
    vec2 imageUV = clamp((uv-.5)/(1.0+breathe)+.5,0.0,1.0);
    vec3 art = texture(sTD2DInputs[1], imageUV).rgb;
    vec3 fluid = texture(sTD2DInputs[0], uv).rgb;
    float pink = pinkMask(art);
    float tissue = smoothstep(.16,.92,dot(art,vec3(.2126,.7152,.0722))) * (1.0-pink);
    vec2 aspect = vec2(1.47,1.0);
    float d = length((uv-gaze.xy)*aspect);
    float dwell = smoothstep(0.0, 1.1, motion.z);
    float focus = gaze.z * (1.0-smoothstep(.015,.084,d));
    float trace = max(fluid.g,fluid.b);
    float activation = pink * max(focus*(.55+.45*dwell), .37*pow(trace,.7));
    // Sample the artwork near gaze to gate the branch response to pink targets.
    float nearSite = 0.0;
    for (int j=0; j<8; ++j) {
        float a = 6.2831853*float(j)/8.0;
        vec2 offset = vec2(cos(a),sin(a))/aspect;
        nearSite = max(nearSite, pinkMask(texture(sTD2DInputs[1],clamp(gaze.xy+offset*.032,0.0,1.0)).rgb));
        nearSite = max(nearSite, pinkMask(texture(sTD2DInputs[1],clamp(gaze.xy+offset*.060,0.0,1.0)).rgb));
    }
    nearSite = max(nearSite,pinkMask(texture(sTD2DInputs[1],gaze.xy).rgb));
    float spread = tissue * pow(trace,.65) * (.26+.65*nearSite*focus);
    vec3 color = art*.30 + vec3(1.0,.22,.44)*activation
               + vec3(.68,.42,.66)*activation*activation
               + vec3(.03,.74,1.0)*spread;
    // An approximate relief based on image luminance, rendered as fine points.
    float lum=dot(art,vec3(.2126,.7152,.0722));
    vec2 cell=floor(uv*vec2(360.,245.));
    vec2 dotUV=fract(uv*vec2(360.,245.))-.5;
    float grain=hashPoint(cell);
    float point=(1.0-smoothstep(.11,.32,length(dotUV)))*smoothstep(.16,.62,lum);
    float relief=clamp(lum-texture(sTD2DInputs[1],clamp(imageUV+vec2(.002,-.002),0.,1.)).r+.5,0.,1.);
    float dissolve=focus*smoothstep(1.0,3.0,motion.z);
    float breakup=step(grain,dissolve*.82);
    color*=1.0-breakup*.86;
    color+=point*vec3(.28,.75,.85)*(.2+relief*.8)*(1.0-dissolve*.65);
    vec2 shifted=uv+vec2((grain-.5)*.022,0.);
    float scattered=1.0-smoothstep(.05,.14,length(fract(shifted*vec2(360.,245.))-.5));
    color+=vec3(.35,.86,1.)*scattered*dissolve*step(.72,grain)*smoothstep(.2,.6,lum);
    // A blink starts a decaying expanding pulse from the last valid gaze.
    float dist=length((uv-wave.xy)*aspect);
    float pulse=exp(-pow((dist-wave.z*.9)*20.0,2.0))*exp(-wave.z*1.8)*step(wave.z,1.2);
    color+=vec3(.55,.92,1.)*pulse*tissue*.9;
    emit(vec4(clamp(color,0.0,1.0),1.0));
}

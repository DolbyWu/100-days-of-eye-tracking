// Fluid, artwork, live parameter texels. Pink marks are interaction targets.
float pinkMask(vec3 rgb) {
    return smoothstep(.08, .21, rgb.r - rgb.g)
         * smoothstep(.25, .57, rgb.r);
}

void main() {
    vec2 uv = vUV.st;
    vec4 gaze = texelFetch(sTD2DInputs[2], ivec2(0,0), 0);
    vec4 motion = texelFetch(sTD2DInputs[2], ivec2(1,0), 0);
    vec3 art = texture(sTD2DInputs[1], uv).rgb;
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
    emit(vec4(clamp(color,0.0,1.0),1.0));
}

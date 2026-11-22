out vec4 fragColor;
ivec2 wrapCell(ivec2 p, ivec2 n) { return (p % n + n) % n; }
vec4 cell(sampler2D t, ivec2 p) { return texelFetch(t, wrapCell(p, textureSize(t,0)), 0); }
vec4 sampleGrid(sampler2D t, vec2 p) {
    ivec2 i = ivec2(floor(p));
    vec2 f = fract(p);
    return mix(mix(cell(t,i),cell(t,i+ivec2(1,0)),f.x),
               mix(cell(t,i+ivec2(0,1)),cell(t,i+1),f.x), f.y);
}
void emit(vec4 c) { fragColor = TDOutputSwizzle(c); }

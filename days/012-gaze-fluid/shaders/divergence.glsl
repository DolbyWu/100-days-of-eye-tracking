void main() {
    ivec2 i = ivec2(vUV.st*vec2(textureSize(sTD2DInputs[0],0)));
    vec2 v = cell(sTD2DInputs[0],i).xy;
    float div = cell(sTD2DInputs[0],i+ivec2(1,0)).x-v.x
              + cell(sTD2DInputs[0],i+ivec2(0,1)).y-v.y;
    emit(vec4(div,0,0,1));
}

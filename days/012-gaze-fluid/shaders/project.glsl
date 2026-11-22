void main() {
    ivec2 i = ivec2(vUV.st*vec2(textureSize(sTD2DInputs[0],0)));
    float p = cell(sTD2DInputs[1],i).r;
    vec2 gradient = p-vec2(cell(sTD2DInputs[1],i-ivec2(1,0)).r,
                           cell(sTD2DInputs[1],i-ivec2(0,1)).r);
    emit(vec4(cell(sTD2DInputs[0],i).xy-gradient,0,1));
}

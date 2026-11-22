void main() {
    vec2 index = vUV.st*vec2(textureSize(sTD2DInputs[0],0))-.5;
    float a = sampleGrid(sTD2DInputs[0],index).r;
    vec2 g = vec2(sampleGrid(sTD2DInputs[0],index+vec2(1,0)).r-a,
                  sampleGrid(sTD2DInputs[0],index+vec2(0,1)).r-a);
    float body = 1.0-exp(-a*.95);
    float filament = 1.0-exp(-length(g)*9.0);
    vec3 color = body*vec3(.015,.32,.48)+pow(filament,1.5)*vec3(.55,.83,.92);
    emit(vec4(clamp(color,0.0,1.0),1));
}

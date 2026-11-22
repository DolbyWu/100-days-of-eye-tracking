#include <OpenGL/OpenGL.h>
#include <OpenGL/gl3.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
static char *readfile(const char *path) {
    FILE *file = fopen(path, "rb");
    if (!file) exit(3);
    fseek(file, 0, SEEK_END);
    size_t n = ftell(file);
    rewind(file);
    char *data = calloc(n + 1, 1);
    if (fread(data, 1, n, file) != n) exit(4);
    fclose(file);
    return data;
}

static GLuint pipeline(GLuint fragment) {
    const char *source = "#version 410 core\nout vec3 vUV; void main(){vec2 xy=vec2((gl_VertexID<<1)&2,gl_VertexID&2); vUV=vec3(xy,0); gl_Position=vec4(xy*2.-1.,0,1);}";
    GLuint vertex = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vertex,1,&source,NULL);
    glCompileShader(vertex);
    GLuint program = glCreateProgram();
    glAttachShader(program,vertex);
    glAttachShader(program,fragment);
    glLinkProgram(program);
    GLint status;
    glGetProgramiv(program,GL_LINK_STATUS,&status);
    if (!status) {
        char log[8192] = {0};
        glGetProgramInfoLog(program,sizeof(log),NULL,log);
        fprintf(stderr,"%s\n",log);
        exit(5);
    }
    return program;
}
static GLuint tex(int width, int height, const float *data) {
    GLuint texture;
    glGenTextures(1,&texture);
    glBindTexture(GL_TEXTURE_2D,texture);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA32F,width,height,0,GL_RGBA,GL_FLOAT,data);
    return texture;
}
static void draw(GLuint program, GLuint output, GLuint a, GLuint b, GLuint c) {
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,output,0);
    if (glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE) exit(6);
    glUseProgram(program);
    GLuint inputs[] = {a,b,c};
    for (int i=0; i<3; ++i) {
        char name[32];
        snprintf(name,sizeof(name),"sTD2DInputs[%d]",i);
        glActiveTexture(GL_TEXTURE0+i);
        glBindTexture(GL_TEXTURE_2D,inputs[i]);
        glUniform1i(glGetUniformLocation(program,name),i);
    }
    glDrawArrays(GL_TRIANGLES,0,3);
}
#define N 256
static float pixels[N*N*4];
static void upload(GLuint texture, const float *values) {
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D,texture);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,4,1,GL_RGBA,GL_FLOAT,values);
}
static double texture_signal(GLuint texture) {
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
    glReadPixels(0,0,N,N,GL_RGBA,GL_FLOAT,pixels);
    double sum=0;
    for(int i=0;i<N*N;i++) {
        float x=pixels[4*i];
        if(!isfinite(x)) exit(7);
        sum+=fabs(x);
    }
    return sum;
}
static void simulate(GLuint *p) {
    GLuint fbo,vao;
    glGenFramebuffers(1,&fbo);
    glBindFramebuffer(GL_FRAMEBUFFER,fbo);
    glGenVertexArrays(1,&vao);
    glBindVertexArray(vao);
    glViewport(0,0,N,N);
    GLuint velocity[2]={tex(N,N,pixels),tex(N,N,pixels)};
    GLuint dye[2]={tex(N,N,pixels),tex(N,N,pixels)};
    GLuint pressure[2]={tex(N,N,pixels),tex(N,N,pixels)};
    GLuint adv=tex(N,N,pixels),div=tex(N,N,pixels),postdiv=tex(N,N,pixels),image=tex(N,N,pixels);
    float values[]={.5,.5,1,.038,.48,-.23,.8,1./60,.5,.5,0,0,210,95,.38,.47};
    GLuint parameters=tex(4,1,values);
    double before=0,after=0,ink=0;
    for(int frame=0;frame<24;frame++) {
        int front=frame%2, back=1-front;
        values[0]=.42+.008*frame;
        if(frame>=12) values[2]=0;
        upload(parameters,values);
        draw(p[0],adv,velocity[front],parameters,0);
        draw(p[1],div,adv,0,0);
        for(int j=0;j<24;j++) draw(p[2],pressure[1-j%2],pressure[j%2],div,0);
        draw(p[3],velocity[back],adv,pressure[0],0);
        draw(p[4],dye[back],dye[front],velocity[back],parameters);
        if(frame==11) {
            draw(p[1],postdiv,velocity[back],0,0);
            before=texture_signal(div);
            after=texture_signal(postdiv);
            ink=texture_signal(dye[back]);
        }
    }
    draw(p[5],image,dye[0],0,0);
    double output=texture_signal(image), persistent=texture_signal(dye[0]);
    printf("Divergence %.4f -> %.4f; dye %.4f -> %.4f after input stops; rendered signal %.4f\n",before,after,ink,persistent,output);
    if(!(after<before && before>0 && persistent<ink && persistent>0 && output>0)) exit(8);
}
int main(int argc, char **argv) {
    CGLPixelFormatAttribute attributes[] = {kCGLPFAOpenGLProfile, (CGLPixelFormatAttribute)kCGLOGLPVersion_GL4_Core, (CGLPixelFormatAttribute)0};
    CGLPixelFormatObj pixel = NULL;
    CGLContextObj context = NULL;
    GLint count = 0;
    CGLError err = CGLChoosePixelFormat(attributes, &pixel, &count);
    if (err || !pixel) { fprintf(stderr, "ChoosePixelFormat: %d\n", err); return 2; }
    err = CGLCreateContext(pixel, NULL, &context);
    if (err || !context || CGLSetCurrentContext(context)) { fprintf(stderr, "Context: %d\n", err); return 2; }
    const char *preamble = "#version 410 core\nuniform sampler2D sTD2DInputs[4];\nin vec3 vUV;\nvec4 TDOutputSwizzle(vec4 c){return c;}\n";
    char *common = readfile(argv[1]);
    printf("Renderer: %s\n", glGetString(GL_RENDERER));
    int failed = 0;
    GLuint programs[6];
    for (int i = 2; i < argc; ++i) {
        char *body = readfile(argv[i]);
        const char *sources[] = {preamble, common, body};
        GLuint shader = glCreateShader(GL_FRAGMENT_SHADER);
        glShaderSource(shader, 3, sources, NULL);
        glCompileShader(shader);
        GLint ok;
        glGetShaderiv(shader, GL_COMPILE_STATUS, &ok);
        char log[8192] = {0};
        glGetShaderInfoLog(shader, sizeof(log), NULL, log);
        printf("%s %s %s\n", ok ? "PASS" : "FAIL", argv[i], log);
        failed |= !ok;
        if(ok) programs[i-2]=pipeline(shader);
        glDeleteShader(shader);
        free(body);
    }
    if(!failed && argc==8) simulate(programs);
    free(common);
    CGLSetCurrentContext(NULL);
    CGLDestroyContext(context);
    CGLDestroyPixelFormat(pixel);
    return failed;
}

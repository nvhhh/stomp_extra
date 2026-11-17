/* Zero-added-latency partitioned convolution for converted vendor captures.
 * Direct head: 64 taps. Tail: fourteen 32-tap partitions, FFT length 64.
 * Tail work is spread over four audio callbacks. The head provides the time
 * needed to compute the tail before its samples are due. Both channels retain
 * independent histories; coefficients are shared. No allocation or interrupts.
 */
typedef unsigned int u32;
typedef struct __attribute__((aligned(32))) {
    float head[72], input[32], work[128], history[14][64];
    float overlap[32], tail[32], ready[32];
    u32 pos, cursor;
    float delayed;
    u32 valid;
} Filter;
typedef struct {
    float controls[2][12];
    float head_coeff[2][64], spectrum[2][14][64];
    Filter filter[2][2];
    u32 mono;
    float *mono_output;
    u32 started;
} Capture;
_Static_assert(sizeof(Capture) <= 32768, "capture exceeds assigned state");

/* Generated constants, rounded once to float32 by the compiler. */
#include "capture_twiddle.h"
extern void partition_head8(float *,const float *,float *);
extern void partition_cmac(float *,const float *,const float *);
static float *hot_coeff(Capture *s) {
    /* The first 256 bytes remain the vendor scratch. The other 3840 bytes
     * exactly fit one head plus fourteen spectra in the slot's existing A. */
    return (float*)(0x3b100+(((u32)s-0x81fa0000)>>15)*0x1000);
}

static void fft32(float *a, int inverse) {
    for (u32 i=1,j=0;i<32;i++) {
        u32 bit=16;
        for (;j&bit;bit>>=1) j^=bit;
        j^=bit;
        if (i<j) {
            float t=a[2*i];a[2*i]=a[2*j];a[2*j]=t;
            t=a[2*i+1];a[2*i+1]=a[2*j+1];a[2*j+1]=t;
        }
    }
    for (u32 len=2;len<=32;len*=2) {
        u32 half=len/2, step=64/len;
        for (u32 i=0;i<32;i+=len) for (u32 j=0;j<half;j++) {
            u32 x=2*(i+j), y=2*(i+j+half), k=j*step;
            float wr=twiddle[2*k], wi=twiddle[2*k+1];
            if(inverse) wi=-wi;
            float re=wr*a[y]-wi*a[y+1], im=wr*a[y+1]+wi*a[y];
            float ar=a[x],ai=a[x+1];
            a[x]=ar+re;a[x+1]=ai+im;a[y]=ar-re;a[y+1]=ai-im;
        }
    }
}
/* A length-64 real transform via one length-32 complex transform. Forward
 * input and inverse output retain the old interleaved-real work convention;
 * inverse scaling remains 64 to keep overlap-add normalization unchanged. */
static void fft(float *a,int inverse) {
    if(!inverse) {
        for(u32 k=0;k<64;k++)a[k]=a[2*k];
        fft32(a,0);
        float re=a[0],im=a[1];a[0]=re+im;a[64]=re-im;a[1]=a[65]=0;
    } else {
        float dc=a[0],ny=a[64];a[0]=(dc+ny)*.5f;a[1]=(dc-ny)*.5f;
    }
    for(u32 k=1;k<16;k++) {
        u32 j=32-k;
        float ar=a[2*k],ai=a[2*k+1],br=a[2*j],bi=a[2*j+1];
        float wr=twiddle[2*k],wi=twiddle[2*k+1];
        float er=(ar+br)*.5f,ei=(ai-bi)*.5f;
        if(!inverse) {
            float ore=(ai+bi)*.5f,oim=(br-ar)*.5f;
            float tr=wr*ore-wi*oim,ti=wr*oim+wi*ore;
            a[2*k]=er+tr;a[2*k+1]=ei+ti;
            a[2*j]=er-tr;a[2*j+1]=-ei+ti;
        } else {
            float tr=(ar-br)*.5f,ti=(ai+bi)*.5f;
            float ore=wr*tr+wi*ti,oim=wr*ti-wi*tr;
            a[2*k]=er-oim;a[2*k+1]=ei+ore;
            a[2*j]=er+oim;a[2*j+1]=-ei+ore;
        }
    }
    a[33]=-a[33];
    if(inverse) {
        fft32(a,1);
        for(int k=63;k>=0;k--){a[2*k]=2*a[k];a[2*k+1]=0;}
    }
}
static void pack(float *dst,const float *src) {
    dst[0]=src[0]; dst[1]=src[64];
    for(u32 k=2;k<64;k++) dst[k]=src[k];
}
static void accumulate(Filter *f, const float coeff[14][64],u32 first,u32 end) {
    float *a=f->work;
    if(!first) for(u32 k=0;k<128;k++) a[k]=0;
    if(end>f->valid)end=f->valid;
    for(u32 p=first;p<end;p++) {
        u32 idx=f->cursor+14-p;if(idx>=14)idx-=14;
        const float *x=f->history[idx],*h=coeff[p];
        a[0]+=x[0]*h[0];a[64]+=x[1]*h[1];
        partition_cmac(a+2,x+2,h+2);
    }
}
static void filter8(Filter *f,const float *head,const float coeff[14][64],
                    const float *input,float *out) {
    u32 phase=(f->pos&31)/8;
    if(phase==0) {
        for(u32 k=0;k<32;k++) {
            f->tail[k]=f->ready[k];
            f->work[2*k]=f->input[k];f->work[2*k+1]=0;
            f->work[64+2*k]=f->work[65+2*k]=0;
        }
        fft(f->work,0);
        if(++f->cursor==14)f->cursor=0;
        if(f->valid<14)f->valid++;
        pack(f->history[f->cursor],f->work);
    } else if(phase==1) accumulate(f,coeff,0,7);
    else if(phase==2) accumulate(f,coeff,7,14);
    else {
        fft(f->work,1);
        for(u32 k=0;k<32;k++) {
            f->ready[k]=f->overlap[k]+f->work[2*k]*(1.0f/64);
            f->overlap[k]=f->work[64+2*k]*(1.0f/64);
        }
    }
    for(u32 i=0;i<8;i++) {
        float v=input[i];f->input[(f->pos+i)&31]=v;f->head[64+i]=v;
    }
    partition_head8(f->head,head,out);
    for(u32 i=0;i<8;i++) {
        float sum=out[i]+f->tail[(f->pos+i)&31];
        out[i]=f->delayed;f->delayed=sum;
    }
    f->pos=(f->pos+8)&63;
    for(u32 i=0;i<64;i++) f->head[i]=f->head[i+8];
}

/* Bounded initialization: one clear slice or one coefficient FFT per call.
 * Metadata cursor belongs to the wrapper, not to this state allocation. */
int partition_init(u32 slot,Capture *s,u32 *meta) {
    u32 cursor=meta[4];
    if(cursor<sizeof(Capture)) {
        u32 end=cursor+512;if(end>sizeof(Capture))end=sizeof(Capture);
        if(cursor<8192) {
            const u32 *raw=(const u32*)(0x60edf000+slot*0x3000+cursor);
            for(u32 k=0;k<128;k++)
                if((raw[k]&0x7f800000)==0x7f800000){meta[1]=2;return 0;}
        }
        for(u32 k=cursor;k<end;k+=4) *(u32*)((char*)s+k)=0;
        meta[4]=end;return 0;
    }
    u32 step=(cursor-sizeof(Capture))/4;
    if(step<28) {
        u32 stage=step/14, part=step%14;
        const float *src=(const float*)(0x60edf000+slot*0x3000+stage*0x1000+0x800);
        float *a=s->filter[0][0].work;
        for(u32 k=0;k<32;k++) {
            float v=src[511-(64+part*32+k)];
            union {float f;u32 u;} bits={v};
            if((bits.u&0x7f800000)==0x7f800000){meta[1]=2;return 0;}
            a[2*k]=v;a[2*k+1]=0;a[64+2*k]=a[65+2*k]=0;
        }
        fft(a,0);
        for(u32 k=0;k<128;k++) {
            union {float f;u32 u;} bits={a[k]};
            if((bits.u&0x7f800000)==0x7f800000){meta[1]=2;return 0;}
        }
        pack(s->spectrum[stage][part],a);
        if(!stage)pack(hot_coeff(s)+64+part*64,a);
        meta[4]=cursor+4;return 0;
    }
    for(u32 stage=0;stage<2;stage++) {
        const float *src=(const float*)(0x60edf000+slot*0x3000+stage*0x1000+0x800);
        for(u32 k=0;k<64;k++) {
            union {float f;u32 u;} bits={src[511-k]};
            if((bits.u&0x7f800000)==0x7f800000){meta[1]=2;return 0;}
            s->head_coeff[stage][k]=bits.f;
            if(!stage)hot_coeff(s)[k]=bits.f;
        }
    }
    /* Stagger four independent filters so each callback executes one forward
     * FFT, two half-products and one inverse FFT, rather than four bursts. */
    for(u32 ch=0;ch<2;ch++) for(u32 stage=0;stage<2;stage++) {
        s->filter[ch][stage].pos=(stage*2+ch)*8;
        for(u32 k=0;k<128;k++)s->filter[ch][stage].work[k]=0;
    }
    s->mono=1;
    /* Do not combine initialization's final work with an audio block. */
    meta[1]=1;return 0;
}

void partition_pair_prepare(const float *left,const float *right,Capture *s) {
    if(!s->mono)return;
    u32 had_history=s->started;s->started=1;
    for(u32 k=0;k<8;k++) {
        union {float f;u32 u;} a={left[k]},b={right[k]};
        if(a.u!=b.u) {
            if(!had_history){s->mono=0;return;}
            /* Both histories were identical up to this callback. Materialize
             * the right history before either channel consumes new input. */
            typedef u32 alias_u32 __attribute__((__may_alias__));
            alias_u32 *dst=(alias_u32*)s->filter[1];
            const alias_u32 *src=(const alias_u32*)s->filter[0];
            for(u32 i=0;i<sizeof(s->filter[0])/4;i++)dst[i]=src[i];
            s->mono=0;return;
        }
    }
}

void partition_core(float *input,float *output,u32 drive,float *channel,float *scratch) {
    Capture *s=(Capture*)((u32)channel&~32767u);
    u32 ch=((u32)channel&32767u)?1:0;
    if(ch && s->mono) {
        for(u32 k=0;k<8;k++)output[k]=s->mono_output[k];
        channel[10]=s->controls[0][10];channel[11]=s->controls[0][11];
        return;
    }
    if(!ch)s->mono_output=output;
    if(drive>100)drive=100;
    channel[11]=((const float*)0x1e5a4)[drive];
    typedef void (*Smooth)(float*,float*,float*,u32,float);
    ((Smooth)0x8675)(input,scratch+3,channel+10,8,0.99f);
    float *hot=hot_coeff(s);
    filter8(&s->filter[ch][0],hot,(const float (*)[64])(hot+64),scratch+3,scratch+19);
    typedef void (*Shape)(float*,float*,const float*,float*,u32,u32);
    ((Shape)0x1b2c9)(scratch+19,scratch+11,(const float*)(0x1e5a4+0x194),scratch,600,8);
    filter8(&s->filter[ch][1],s->head_coeff[1],s->spectrum[1],scratch+11,scratch+27);
    typedef void (*Copy)(float*,float*,u32,float);
    ((Copy)0x8561)(scratch+27,output,8,1.0f);
}

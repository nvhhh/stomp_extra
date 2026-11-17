/* Long user cab IRs (1024 taps) with zero-added-latency partitioned convolution.
 *
 * Built only for --long-ir. Includes the capture kernel unchanged and reuses its
 * FFT, packing and assembly helpers (same algorithm, verified on the captures):
 * direct 64-tap head, tail of thirty 32-tap partitions (taps 64..1023), FFT
 * length 64, tail work spread over four audio callbacks, one-sample output
 * delay like the stock FIR. Output equals the direct 1024-tap FIR up to
 * floating-point rounding.
 *
 * Partition spectra are computed by cab_load() in the main loop, right after the
 * stock IR loader copies the slot's coefficients; the audio callback never pays
 * for setup. The CAB processor does not run its FIR while an IR is loading.
 */
#include "capture_partitioned.c"

#define CAB_PARTS 30
#define CAB_COEFFS ((const float *)(0x20004998 + 0x128))   /* 2048 floats, IR reversed */
typedef struct __attribute__((aligned(32))) {
    float head[72], input[32], work[128], history[CAB_PARTS][64];
    float overlap[32], tail[32], ready[32];
    u32 pos, cursor;
    float delayed;
    u32 valid;
} CabFilter;
typedef struct {
    float head_coeff[64];
    float spectrum[CAB_PARTS][64];
    volatile u32 loaded;          /* active CAB index + 1 whose spectra are ready, 0 = none */
    CabFilter f;
} Cab;
_Static_assert(sizeof(Cab) <= 32768, "cab state exceeds its cacheable SDRAM window");
#define CAB ((Cab *)0x81fb8000)

static int finite(float v) {
    union {float f; u32 u;} bits = {v};
    return (bits.u & 0x7f800000) != 0x7f800000;
}

static void cab_accumulate(CabFilter *f, const float coeff[CAB_PARTS][64], u32 first, u32 end) {
    float *a = f->work;
    if (!first) for (u32 k = 0; k < 128; k++) a[k] = 0;
    if (end > f->valid) end = f->valid;
    for (u32 p = first; p < end; p++) {
        u32 idx = f->cursor + CAB_PARTS - p; if (idx >= CAB_PARTS) idx -= CAB_PARTS;
        const float *x = f->history[idx], *h = coeff[p];
        a[0] += x[0] * h[0]; a[64] += x[1] * h[1];
        partition_cmac(a + 2, x + 2, h + 2);
    }
}

static void cab_filter8(CabFilter *f, const float *head, const float coeff[CAB_PARTS][64],
                        const float *input, float *out) {
    u32 phase = (f->pos & 31) / 8;
    if (phase == 0) {
        for (u32 k = 0; k < 32; k++) {
            f->tail[k] = f->ready[k];
            f->work[2*k] = f->input[k]; f->work[2*k+1] = 0;
            f->work[64+2*k] = f->work[65+2*k] = 0;
        }
        fft(f->work, 0);
        if (++f->cursor == CAB_PARTS) f->cursor = 0;
        if (f->valid < CAB_PARTS) f->valid++;
        pack(f->history[f->cursor], f->work);
    } else if (phase == 1) cab_accumulate(f, coeff, 0, CAB_PARTS / 2);
    else if (phase == 2) cab_accumulate(f, coeff, CAB_PARTS / 2, CAB_PARTS);
    else {
        fft(f->work, 1);
        for (u32 k = 0; k < 32; k++) {
            f->ready[k] = f->overlap[k] + f->work[2*k] * (1.0f/64);
            f->overlap[k] = f->work[64+2*k] * (1.0f/64);
        }
    }
    for (u32 i = 0; i < 8; i++) {
        float v = input[i]; f->input[(f->pos+i) & 31] = v; f->head[64+i] = v;
    }
    partition_head8(f->head, head, out);
    for (u32 i = 0; i < 8; i++) {
        float sum = out[i] + f->tail[(f->pos+i) & 31];
        out[i] = f->delayed; f->delayed = sum;
    }
    f->pos = (f->pos + 8) & 63;
    for (u32 i = 0; i < 64; i++) f->head[i] = f->head[i+8];
}

/* Main loop, after the stock loader copied IR `index` into the CAB object. */
void cab_load(u32 index) {
    Cab *c = CAB;
    c->loaded = 0;
    if (index < 240 || index >= 250) return;
    const float *src = CAB_COEFFS;
    for (u32 k = 0; k < 64; k++) {
        float v = src[2047 - k];
        if (!finite(v)) return;
        c->head_coeff[k] = v;
    }
    float *a = c->f.work;
    for (u32 p = 0; p < CAB_PARTS; p++) {
        for (u32 k = 0; k < 32; k++) {
            float v = src[2047 - (64 + p*32 + k)];
            if (!finite(v)) return;
            a[2*k] = v; a[2*k+1] = 0; a[64+2*k] = a[65+2*k] = 0;
        }
        fft(a, 0);
        for (u32 k = 0; k < 128; k++) if (!finite(a[k])) return;
        pack(c->spectrum[p], a);
    }
    typedef u32 alias_u32 __attribute__((__may_alias__));
    alias_u32 *z = (alias_u32 *)&c->f;
    for (u32 i = 0; i < sizeof(CabFilter) / 4; i++) z[i] = 0;
    c->loaded = index + 1;
}

/* Audio callback: 1 = processed `in` (8 samples) into `out`; 0 = caller uses the stock path. */
int cab_process(const float *in, float *out, u32 active) {
    Cab *c = CAB;
    if (active < 240 || active >= 250 || c->loaded != active + 1) return 0;
    cab_filter8(&c->f, c->head_coeff, c->spectrum, in, out);
    return 1;
}

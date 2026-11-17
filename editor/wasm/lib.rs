//! open-stomp's converters for the browser (no wasm-bindgen; plain C ABI).
//!
//! JS: `alloc(n)` → write the input file → `ir_convert(ptr, len, method)` or
//! `nam_convert(ptr, len)` → 0 on success, then read `out_ptr()/out_len()`;
//! nonzero → read the message from `err_ptr()/err_len()`. A panic traps the instance after
//! storing its message, so create a fresh instance per conversion.
//!
//! Outputs: IR → 8192 bytes (2048 little-endian f32, the slot upload).
//! NAM → 8192 bytes upload + 4 bytes f32 slot factor + 4 bytes f32 optimiser loss (lowest).

use open_stomp::{ir, nam};

static mut OUT: Vec<u8> = Vec::new();
static mut ERR: Vec<u8> = Vec::new();

#[link(wasm_import_module = "env")]
unsafe extern "C" {
    /// Optimiser progress (step, total), provided by the page.
    fn progress(done: u32, total: u32);
}

fn set_err(msg: &str) {
    unsafe { *(&raw mut ERR) = msg.as_bytes().to_vec() }
}

fn set_out(v: Vec<u8>) {
    unsafe { *(&raw mut OUT) = v }
}

fn install_panic_hook() {
    std::panic::set_hook(Box::new(|info| {
        let msg = info
            .payload()
            .downcast_ref::<&str>()
            .map(|s| s.to_string())
            .or_else(|| info.payload().downcast_ref::<String>().cloned())
            .unwrap_or_else(|| "converter error".into());
        set_err(&msg);
    }));
}

#[unsafe(no_mangle)]
pub extern "C" fn alloc(n: usize) -> *mut u8 {
    let mut v = vec![0u8; n];
    let p = v.as_mut_ptr();
    std::mem::forget(v);
    p
}

#[unsafe(no_mangle)]
pub extern "C" fn out_ptr() -> *const u8 {
    unsafe { (*(&raw const OUT)).as_ptr() }
}

#[unsafe(no_mangle)]
pub extern "C" fn out_len() -> usize {
    unsafe { (*(&raw const OUT)).len() }
}

#[unsafe(no_mangle)]
pub extern "C" fn err_ptr() -> *const u8 {
    unsafe { (*(&raw const ERR)).as_ptr() }
}

#[unsafe(no_mangle)]
pub extern "C" fn err_len() -> usize {
    unsafe { (*(&raw const ERR)).len() }
}

fn f32_bytes(v: &[f32]) -> Vec<u8> {
    v.iter().flat_map(|x| x.to_le_bytes()).collect()
}

/// `method`: 0 = app (Stomp Manager), 1 = optimised (Accurate).
#[unsafe(no_mangle)]
pub extern "C" fn ir_convert(ptr: *const u8, len: usize, method: u32) -> i32 {
    install_panic_hook();
    let bytes = unsafe { std::slice::from_raw_parts(ptr, len) };
    let wav = match ir::Wav::parse(bytes) {
        Ok(w) => w,
        Err(e) => {
            set_err(&format!("not a usable WAV file: {e}"));
            return 1;
        }
    };
    let m = if method == 1 { ir::Method::Optimised } else { ir::Method::App };
    let c = ir::convert_with(&wav, m);
    if c.data.len() != 2048 || c.data.iter().any(|x| !x.is_finite()) {
        set_err("IR conversion produced invalid data");
        return 2;
    }
    set_out(f32_bytes(&c.data));
    0
}

/// Accurate NAM conversion (open-stomp's optimised fit; never needs Stomp Manager).
#[unsafe(no_mangle)]
pub extern "C" fn nam_convert(ptr: *const u8, len: usize) -> i32 {
    install_panic_hook();
    let bytes = unsafe { std::slice::from_raw_parts(ptr, len) };
    let text = match std::str::from_utf8(bytes) {
        Ok(t) => t,
        Err(_) => {
            set_err("not a .nam file (not text)");
            return 1;
        }
    };
    let mut model = match nam::Model::from_json_str(text) {
        Ok(m) => m,
        Err(e) => {
            set_err(&format!("unsupported .nam file: {e}"));
            return 1;
        }
    };
    // Same steps as nam::convert::convert_optimised, keeping the optimiser's loss for checks.
    let x = nam::convert::excitation();
    let clean = nam::convert::convert_measured(&mut model, &x, nam::convert::Measure::Clean);
    let o = nam::optimise::optimise_with_progress(
        &mut model,
        &clean.data,
        &nam::optimise::Options::default(),
        &mut |done, total| {
            unsafe { progress(done as u32, total as u32) };
            true
        },
    );
    if o.data.len() != 2048 || o.data.iter().any(|x| !x.is_finite()) || !clean.factor.is_finite() {
        set_err("NAM conversion produced invalid data");
        return 2;
    }
    let best = o.loss.iter().copied().fold(o.initial_loss, f64::min) as f32;
    let mut out = f32_bytes(&o.data);
    out.extend_from_slice(&clean.factor.to_le_bytes());
    out.extend_from_slice(&best.to_le_bytes());
    set_out(out);
    0
}

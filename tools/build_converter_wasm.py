"""Build editor/static/stomp_convert.wasm: open-stomp's NAM/IR converters for the browser editor.

Needs Rust with the wasm32-unknown-unknown target (rustup target add wasm32-unknown-unknown).
Fetches open-stomp at a fixed tag into work/open-stomp-src and applies one patch: the optimiser's
work-stealing pool runs inline when only one thread is available (wasm has no threads).

usage: python tools/build_converter_wasm.py
"""
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG = "v0.6.1"
REPO = "https://github.com/JackMechem/open-stomp-lib.git"
SRC = ROOT / "work" / "open-stomp-src"
CRATE = ROOT / "editor" / "wasm"
OUT = ROOT / "editor" / "static" / "stomp_convert.wasm"

PAR_MAP_OLD = """    let threads = std::thread::available_parallelism().map_or(1, |t| t.get()).clamp(1, 16).min(n.max(1));
    let mut done: Vec<(usize, T)> = std::thread::scope(|s| {"""
PAR_MAP_NEW = """    let threads = std::thread::available_parallelism().map_or(1, |t| t.get()).clamp(1, 16).min(n.max(1));
    if threads == 1 {
        return (0..n).map(&f).collect();
    }
    let mut done: Vec<(usize, T)> = std::thread::scope(|s| {"""


def fetch():
    if not (SRC / "Cargo.toml").exists():
        SRC.parent.mkdir(exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", TAG, REPO, str(SRC)], check=True)
    tag = subprocess.check_output(["git", "-C", str(SRC), "describe", "--tags", "--exact-match"], text=True).strip()
    assert tag == TAG, f"{SRC} is at {tag}, expected {TAG} (delete it to refetch)"
    opt = SRC / "src" / "nam" / "optimise.rs"
    text = opt.read_text(encoding="utf-8")
    if PAR_MAP_NEW not in text:
        assert text.count(PAR_MAP_OLD) == 1, "open-stomp optimiser changed; update the patch"
        opt.write_text(text.replace(PAR_MAP_OLD, PAR_MAP_NEW), encoding="utf-8")


def main():
    fetch()
    cargo = shutil.which("cargo") or str(Path.home() / ".cargo" / "bin" / "cargo")
    subprocess.run([cargo, "build", "--release", "--target", "wasm32-unknown-unknown"], cwd=CRATE, check=True)
    built = CRATE / "target" / "wasm32-unknown-unknown" / "release" / "stomp_convert.wasm"
    shutil.copyfile(built, OUT)
    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size} bytes (open-stomp {TAG})")


if __name__ == "__main__":
    main()

"""Read model names and parameter labels from Stomp Manager's Edit panel (screenshots + Windows OCR).

usage: sm_scrape.py <out.json> [module ...]

Clicks the module column, then every model in the model list (scrolling as needed), and OCRs the
parameter panel. Changes only the pedal's edit buffer; nothing is saved.
"""
import asyncio
import ctypes as C
import ctypes.wintypes as W
import json
import os
import re
import sys
import tempfile
import time

from PIL import Image
from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.storage import FileAccessMode, StorageFile

C.windll.shcore.SetProcessDpiAwareness(2)
u32, g32 = C.windll.user32, C.windll.gdi32
TMP = tempfile.mkdtemp(prefix="smscrape_")

# Edit-panel geometry in window pixels (measured at 1152x784).
MODULES = {"GATE": 320, "OD/FX": 363, "AMP": 405, "CAB": 448, "EQ": 491, "MOD": 533, "DEL": 576, "REV": 619}
MODULE_X = 380
LIST_BOX = (470, 295, 690, 775)
PARAM_BOX = (700, 295, 1145, 775)


def hwnd():
    h = u32.FindWindowW(None, "Stomp Manager")
    if not h:
        sys.exit("Stomp Manager window not found")
    return h


def rect(h):
    r = W.RECT()
    u32.GetWindowRect(h, C.byref(r))
    return r.left, r.top, r.right, r.bottom


def grab(h):
    l, t, r, b = rect(h)
    w, ht = r - l, b - t
    hdc = u32.GetWindowDC(h)
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, ht)
    g32.SelectObject(mdc, bmp)
    u32.PrintWindow(h, mdc, 2)

    class BMI(C.Structure):
        _fields_ = [("biSize", W.DWORD), ("biWidth", W.LONG), ("biHeight", W.LONG), ("biPlanes", W.WORD),
                    ("biBitCount", W.WORD), ("biCompression", W.DWORD), ("biSizeImage", W.DWORD),
                    ("biXPelsPerMeter", W.LONG), ("biYPelsPerMeter", W.LONG), ("biClrUsed", W.DWORD),
                    ("biClrImportant", W.DWORD)]
    bi = BMI(C.sizeof(BMI), w, -ht, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = C.create_string_buffer(w * ht * 4)
    g32.GetDIBits(mdc, bmp, 0, ht, buf, C.byref(bi), 0)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(h, hdc)
    return Image.frombuffer("RGBA", (w, ht), buf, "raw", "BGRA", 0, 1).convert("RGB")


async def _ocr(path):
    f = await StorageFile.get_file_from_path_async(path)
    s = await f.open_async(FileAccessMode.READ)
    bmp = await (await BitmapDecoder.create_async(s)).get_software_bitmap_async()
    res = await OcrEngine.try_create_from_user_profile_languages().recognize_async(bmp)
    return [(l.text, min(w.bounding_rect.y for w in l.words), min(w.bounding_rect.x for w in l.words))
            for l in res.lines]


def ocr(img, box, scale=2):
    crop = img.crop(box).resize(((box[2] - box[0]) * scale, (box[3] - box[1]) * scale), Image.LANCZOS)
    p = os.path.join(TMP, "c.png")
    crop.save(p)
    lines = asyncio.run(_ocr(p))
    return [(t, box[1] + y / scale, box[0] + x / scale) for t, y, x in lines]


def click(h, x, y):
    u32.SetForegroundWindow(h)
    l, t, _, _ = rect(h)
    u32.SetCursorPos(l + int(x), t + int(y))
    time.sleep(0.05)
    u32.mouse_event(0x0002, 0, 0, 0, 0)
    u32.mouse_event(0x0004, 0, 0, 0, 0)


def wheel(h, x, y, notches):
    u32.SetForegroundWindow(h)
    l, t, _, _ = rect(h)
    u32.SetCursorPos(l + int(x), t + int(y))
    for _ in range(abs(notches)):
        u32.mouse_event(0x0800, 0, 0, C.c_uint32(-120 if notches > 0 else 120).value, 0)
        time.sleep(0.03)


ITEM = re.compile(r"^\s*([0-9OoIl|]{1,2})\s*[.,]\s*(.+?)\s*$")


def digits(s):
    return int(s.translate(str.maketrans("OoIl|", "00111")))


def model_items(img):
    out = []
    for t, y, x in ocr(img, LIST_BOX):
        m = ITEM.match(t)
        if m:
            try:
                out.append((digits(m.group(1)), m.group(2), y))
            except ValueError:
                pass
    return out


def params(img):
    lines = sorted(ocr(img, PARAM_BOX), key=lambda a: a[1])
    labels, values, state = [], [], None
    for t, y, x in lines:
        if t.strip().upper() in ("OFF", "ON"):
            state = t.strip().upper()
        elif t.rstrip().endswith(":"):
            labels.append(t.rstrip(" :"))
        elif re.fullmatch(r"-?[0-9OIl.]+\s*\w*", t.strip()):
            values.append(t.strip())
        else:
            labels.append(t.strip())
    return {"labels": labels, "values": values, "state": state}


def scrape_module(h, mod):
    click(h, MODULE_X, MODULES[mod])
    time.sleep(0.6)
    wheel(h, 580, 500, -30)  # scroll model list to top
    time.sleep(0.4)
    seen, results, stale = set(), [], 0
    while stale < 2:
        items = model_items(grab(h))
        new = [it for it in items if it[0] not in seen]
        if not new:
            stale += 1
        for num, name, y in new:
            seen.add(num)
            click(h, 560, y + 12)
            time.sleep(0.45)
            p = params(grab(h))
            for _ in range(4):  # long parameter lists (10-band EQ) scroll inside the panel
                wheel(h, 900, 600, 3)
                time.sleep(0.35)
                more = params(grab(h))
                extra = [l for l in more["labels"] if l not in p["labels"]]
                if not extra:
                    break
                p["labels"] += extra
            wheel(h, 900, 600, -12)
            results.append({"num": num, "name": name, **p})
            print(f"  {mod:6s} {num:02d} {name:22s} {p['labels']}", flush=True)
        wheel(h, 580, 500, 2)
        time.sleep(0.4)
    return sorted(results, key=lambda r: r["num"])


def main():
    out = sys.argv[1]
    mods = sys.argv[2:] or list(MODULES)
    h = hwnd()
    data = json.load(open(out)) if os.path.exists(out) else {}
    for m in mods:
        print("==", m, flush=True)
        data[m] = scrape_module(h, m)
        json.dump(data, open(out, "w"), indent=1)
    print("saved", out)


if __name__ == "__main__":
    main()

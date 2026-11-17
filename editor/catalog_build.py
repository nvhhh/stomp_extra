"""Build editor/catalog.json: modules, models and parameter labels for the JME / Dual Stomp Lite.

Inputs: the model/label list read from Stomp Manager's edit panel (tools/sm_scrape.py output) plus
the protocol layout reverse engineered from the preset record (docs/PROTOCOL.md).

usage: catalog_build.py <sm_models.json> <catalog.json>
"""
import json
import re
import sys

# Record layout. slot = index in record bytes 0..7 (value = model | 0x40 when bypassed, CC n = slot n).
# block = (count byte offset, CC of first parameter, capacity).
MODULES = [
    # key      label    slot  count  cc   cap  color
    ("GATE",  "Gate",    6,   8,    8,   4, "#b5b02a"),
    ("OD/FX", "OD/FX",   0,  13,   12,   6, "#e3b400"),
    ("AMP",   "Amp",     1,  20,   18,   8, "#ef4a1e"),
    ("CAB",   "Cab",     2,  29,   26,   6, "#ef7c12"),
    ("EQ",    "EQ",      7,  36,   32,  12, "#b07ce6"),
    ("MOD",   "Mod",     3,  49,   44,   4, "#3fae2a"),
    ("DEL",   "Delay",   4,  54,   48,   6, "#1d8de0"),
    ("REV",   "Reverb",  5,  61,   54,   4, "#7a1fe6"),
]

NAME_FIX = {
    "Chorus-I": "Chorus-1", "DSI": "DS1", "voxy 30HW": "Voxy 30HW", "voxy 212": "Voxy 212",
    "ODS-IOO": "ODS-100", "Mar 412": "Mar V30 412", "Io-band EQ": "10-band EQ", "IO-band EQ": "10-band EQ",
}
LABEL_FIX = {"LEVEY": "LEVEL", "LEVEE": "LEVEL", "IOOHz(dB)": "100Hz(dB)", "Distortion": "DISTORTION"}

# Verified against factory presets (raw value -> name shown by Stomp Manager).
MIC = ["M160", "E906", "MD421", "R121", "SM57", "SM58", "SM7B", "U47"]
POSITION = ["EDGE", "MIDDLE", "CENTER"]
# Selector parameters whose option order could not be verified: shown as numbered choices.
UNVERIFIED_ENUM = {
    ("MOD", "Chorus+", "MODE"): 2, ("MOD", "Uni Vibe", "MODE"): 2,
    ("MOD", "Harmony", "KEY"): 12, ("MOD", "Harmony", "MODE"): 2,
}
# Values Stomp Manager shows next to a selector label (OCR picked them up as extra lines).
VALUE_TOKENS = set(MIC) | set(POSITION) | {"I-J47", "CHORUS", "VIBRATO", "MINOR", "MAJOR", "C", "c", "e"}

# User IR cabs (models 30..39) keep the built-in cab block layout: the pedal resets MIC/POSITION to 0
# and Stomp Manager only shows LOW CUT, HIGH CUT and VOLUME, which stay at positions 2..4 (CC 28..30,
# record offsets 32..34). Selecting an IR slot on the pedal loads [0, 0, 0, 100, 50] into the block.
IR_CAB_LABELS = ["LOW CUT(Hz)", "HIGH CUT(Hz)", "VOLUME"]
IR_CAB_FIRST_POS = 2

EQ10 = ["GAIN(dB)", "31Hz(dB)", "62.5Hz(dB)", "125Hz(dB)", "250Hz(dB)", "500Hz(dB)",
        "1kHz(dB)", "2kHz(dB)", "4kHz(dB)", "8kHz(dB)", "16kHz(dB)", "VOLUME(dB)"]


def clean_label(s):
    s = re.sub(r"[^\w()%./ +-]+.*$", "", s.strip())       # drop OCR junk tails like '�.'
    s = re.sub(r"[-.]+$", "", s).strip()
    s = re.sub(r"\s+\(", "(", s).replace(" Hz", "Hz")
    return LABEL_FIX.get(s, s)


def params_for(mod, name, labels, first_pos=0):
    """Parameters in block order. 'pos' = position in the block: CC = cc_base + pos,
    record offset = count_offset + 1 + pos."""
    if mod == "EQ" and name.startswith("10"):
        labels = EQ10
    out = []
    after_selector = False
    for raw in labels:
        lab = clean_label(raw)
        if not lab:
            continue
        if after_selector and lab in VALUE_TOKENS:  # the selector's current value, not a label
            after_selector = False
            continue
        after_selector = lab in ("MIC", "POSITION", "MODE", "KEY")
        p = {"label": lab, "pos": first_pos + len(out)}
        if mod == "CAB" and lab == "MIC":
            p.update(type="enum", options=MIC)
        elif mod == "CAB" and lab == "POSITION":
            p.update(type="enum", options=POSITION)
        elif (mod, name, lab) in UNVERIFIED_ENUM:
            n = UNVERIFIED_ENUM[(mod, name, lab)]
            p.update(type="enum", options=[f"#{i}" for i in range(n)], verified=False)
        out.append(p)
    return out


def main():
    src = json.load(open(sys.argv[1], encoding="utf-8"))
    cat = {"modules": [], "chain_default": [6, 0, 1, 2, 7, 3, 4, 5],
           "volume": {"offset": 66, "cc": 58}, "name": {"offset": 82, "length": 16},
           "chain": {"offset": 70, "length": 8}}
    for key, label, slot, cnt, cc, cap, color in MODULES:
        models = []
        for m in sorted(src[key], key=lambda r: r["num"]):
            name = NAME_FIX.get(m["name"], m["name"])
            user = None
            if key == "AMP" and m["num"] > 30:
                user = {"kind": "nam", "slot": m["num"] - 31}
            if key == "CAB" and m["num"] > 30:
                user = {"kind": "ir", "slot": m["num"] - 31}
            labels, first_pos = m["labels"], 0
            if user and key == "CAB":
                labels, first_pos = IR_CAB_LABELS, IR_CAB_FIRST_POS
            models.append({"index": m["num"] - 1, "name": name if not user else None,
                           "user": user, "params": params_for(key, name, labels, first_pos)})
        if key == "CAB":  # IR slot 1 was empty in the scrape; user slots share one layout
            have = {mm["index"] for mm in models}
            for i in range(30, 40):
                if i not in have:
                    models.append({"index": i, "name": None, "user": {"kind": "ir", "slot": i - 30},
                                   "params": params_for("CAB", "", IR_CAB_LABELS, IR_CAB_FIRST_POS)})
            models.sort(key=lambda mm: mm["index"])
        cat["modules"].append({"key": key, "label": label, "slot": slot, "count_offset": cnt,
                               "cc_base": cc, "capacity": cap, "color": color, "models": models})
    json.dump(cat, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
    for m in cat["modules"]:
        print(f'{m["key"]:6s} {len(m["models"]):3d} models, params/model: '
              f'{sorted({len(x["params"]) for x in m["models"]})}')


if __name__ == "__main__":
    main()

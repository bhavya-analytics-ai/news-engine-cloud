#!/usr/bin/env python3
"""Validate tag files against their input batches. usage: validate_tags.py <batches_dir> <tags_dir> <required_fields_csv>
Exit 1 and print every problem if any batch is missing, has a different line count, a different id order, or an unparseable line.
"""
import json, os, sys, glob
bd, td, req = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
problems = 0
for bf in sorted(glob.glob(os.path.join(bd, "*.jsonl"))):
    name = os.path.basename(bf); tf = os.path.join(td, name)
    ids = [json.loads(l)["id"] for l in open(bf) if l.strip()]
    if not os.path.exists(tf):
        print(f"MISSING {name}"); problems += 1; continue
    out = []
    for n, l in enumerate(open(tf), 1):
        l = l.strip()
        if not l: continue
        try:
            o = json.loads(l)
        except Exception as e:
            print(f"BAD JSON {name} line {n}: {e}"); problems += 1; continue
        miss = [k for k in req if k not in o]
        if miss: print(f"MISSING FIELDS {name} line {n}: {miss}"); problems += 1
        out.append(o.get("id"))
    if len(out) != len(ids):
        print(f"LINE COUNT {name}: input {len(ids)} output {len(out)}"); problems += 1
    elif out != ids:
        first = next(i for i, (a, b) in enumerate(zip(out, ids)) if a != b)
        print(f"ID ORDER {name}: first mismatch at line {first+1} (expected {ids[first]}, got {out[first]})"); problems += 1
print("OK" if problems == 0 else f"{problems} PROBLEMS")
sys.exit(1 if problems else 0)

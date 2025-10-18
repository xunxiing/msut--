#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
程序 A：为 .melsave 生成"方向无关"的唯一数字水印，并写入测试环境 JSON（test-only）。

要点：
  1) 支持 saveObjectContainers 结构；统一 instanceId 为整数，稳定排序。
  2) 规范化方向：canon(seq) = min(seq, list(reversed(seq)))  （按字典序比较）
  3) 水印与保存的 sequence 一律使用 canon(seq)。

用法：
  python watermark_indexer.py --input .\saves_dir --registry .\test_registry.json
或
  python watermark_indexer.py --input .\one.melsave --registry .\test_registry.json
"""

import argparse, csv, io, json, os, time, zipfile, re
from typing import Any, List, Optional, Tuple

TEST_ENV_BANNER = "TEST_ONLY_DO_NOT_USE_IN_PROD"
_INT_RE = re.compile(r'^[+-]?\d+$')

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _read_text_guess_utf8(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="ignore")

def _norm_iid(x) -> Optional[int]:
    if x is None:
        return None
    if isinstance(x, int):
        return x
    if isinstance(x, str) and _INT_RE.match(x.strip()):
        try:
            return int(x.strip())
        except Exception:
            return None
    return None

def canonicalize(seq: List[str]) -> List[str]:
    """方向无关规范化：在 seq 与其反转之间取字典序更小者。"""
    rev = list(reversed(seq))
    return seq if seq <= rev else rev

def fnv1a64(seq: List[str]) -> int:
    """对规范化后的序列做 64 位 FNV-1a。"""
    FNV_OFFSET = 14695981039346656037
    FNV_PRIME = 1099511628211
    h = FNV_OFFSET
    for idx, tok in enumerate(seq):
        piece = f"{idx}#{tok}".encode("utf-8", errors="ignore")
        for b in piece:
            h ^= b
            h = (h * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h

# -------------------- 解析 Data --------------------
def _extract_seq_from_containers(obj: dict) -> Optional[List[str]]:
    if not isinstance(obj, dict) or "saveObjectContainers" not in obj:
        return None
    rows: List[Tuple[Optional[int], int, str]] = []  # (iid_norm, first_seen, oid)
    seen = 0

    def collect(node: Any):
        nonlocal seen
        if node is None:
            return
        if isinstance(node, dict):
            if "objectId" in node:
                oid = str(node.get("objectId"))
                iid = _norm_iid(node.get("instanceId"))
                rows.append((iid, seen, oid))
                seen += 1
            for k in ("items", "children", "saveObjects", "saveObjectChildren"):
                v = node.get(k)
                if isinstance(v, list):
                    for it in v: collect(it)
                elif isinstance(v, dict):
                    collect(v)
        elif isinstance(node, list):
            for it in node: collect(it)

    for c in obj.get("saveObjectContainers", []):
        if isinstance(c, dict):
            collect(c.get("saveObjects"))
            children = c.get("saveObjectChildren")
            if isinstance(children, list):
                for ch in children:
                    collect(ch.get("saveObjects") if isinstance(ch, dict) else ch)

    if not rows:
        return []
    # 稳定排序：有 iid 的在前，按 iid 升序；无 iid 的按首次出现顺序。
    rows.sort(key=lambda t: (t[0] is None, t[0] if t[0] is not None else 0, t[1]))
    return [oid for (_iid, _idx, oid) in rows]

def _coerce_common(obj: Any) -> Optional[List[str]]:
    def coerce_seq(objs: List[Any]) -> List[str]:
        if not objs:
            return []
        if isinstance(objs[0], dict) and "objectId" in objs[0]:
            if "instanceId" in objs[0]:
                def key(d):
                    iid = _norm_iid(d.get("instanceId"))
                    return (iid is None, iid if iid is not None else 0)
                objs = sorted(objs, key=key)
            return [str(d["objectId"]) for d in objs]
        return [str(x) for x in objs]
    if isinstance(obj, dict):
        if isinstance(obj.get("objects"), list):
            return coerce_seq(obj["objects"])
        if isinstance(obj.get("sequence"), list):
            return [str(x) for x in obj["sequence"]]
    if isinstance(obj, list):
        return coerce_seq(obj)
    return None

def _parse_seq_from_json(text: str) -> Optional[List[str]]:
    try:
        obj = json.loads(text)
    except Exception:
        return None
    seq = _extract_seq_from_containers(obj)
    if isinstance(seq, list):
        return seq
    return _coerce_common(obj)

def _parse_seq_from_csv(text: str) -> Optional[List[str]]:
    buf = io.StringIO(text)
    try:
        rdr = csv.DictReader(buf)
        rows = list(rdr)
        if not rows or "objectId" not in (rdr.fieldnames or []):
            return None
        if "instanceId" in rdr.fieldnames:
            rows.sort(key=lambda r: (_norm_iid(r.get("instanceId")) is None,
                                     _norm_iid(r.get("instanceId")) or 0))
        return [str(r["objectId"]) for r in rows]
    except Exception:
        return None

def _parse_seq_from_text(text: str) -> Optional[List[str]]:
    vals = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return vals or None

def extract_sequence_from_melsave(path: str) -> Tuple[List[str], Optional[int]]:
    """返回：原始序列 raw_seq（未规范化）、embedded_wm（若有）"""
    embedded = None
    with zipfile.ZipFile(path, "r") as zf:
        # 读取内嵌水印（如果你们以后写进去）
        for name in zf.namelist():
            low = name.lower()
            if low.endswith(("watermark.json", "wm.json", "watermark.txt", "wm.txt")):
                try:
                    s = _read_text_guess_utf8(zf.read(name)).strip()
                    if s.startswith("{"):
                        v = json.loads(s).get("watermark_u64")
                        if isinstance(v, int):
                            embedded = v
                    else:
                        embedded = int(s)
                except Exception:
                    pass
                break
        # 找 Data
        cands = []
        for name in zf.namelist():
            base = os.path.basename(name)
            if base in ("Data", "data", "Data.json", "data.json", "Data.csv", "data.csv",
                        "sequence.txt", "objects.txt"):
                cands.append(name)
        if not cands:
            for name in zf.namelist():
                low = name.lower()
                if low.endswith(("/data", "/data.json", "/data.csv", "data", "data.json", "data.csv")):
                    cands.append(name)
        if not cands:
            raise RuntimeError(f"{path} 内未找到 Data")
        def weight(n: str) -> int:
            nlow = n.lower()
            if nlow.endswith((".json", "/data.json")) or os.path.basename(n).lower() in ("data","data.json"):
                return 0
            if nlow.endswith((".csv", "/data.csv")) or os.path.basename(n).lower() in ("data.csv",):
                return 1
            return 2
        cands.sort(key=weight)
        text = _read_text_guess_utf8(zf.read(cands[0]))
        for p in (_parse_seq_from_json, _parse_seq_from_csv, _parse_seq_from_text):
            raw = p(text)
            if raw is not None:
                return raw, embedded
        raise RuntimeError(f"{path} 的 Data 无法解析")

# -------------------- registry I/O --------------------
def load_registry(path: str) -> dict:
    if not os.path.exists(path):
        return {"env": TEST_ENV_BANNER, "version": 1, "created_at": _now_iso(), "entries": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_registry(path: str, obj: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

# -------------------- 主流程 --------------------
def index_one(melsave_path: str, registry: dict) -> dict:
    raw_seq, embedded_wm = extract_sequence_from_melsave(melsave_path)
    seq = canonicalize([str(x) for x in raw_seq])   # 方向无关
    wm = fnv1a64(seq)
    entry = {
        "save_name": os.path.basename(melsave_path),
        "save_path": os.path.abspath(melsave_path),
        "length": len(seq),
        "watermark_u64": int(wm),
        "sequence": seq,                  # 注意：已是 canon(seq)
        "embedded_watermark": embedded_wm,
        "indexed_at": _now_iso()
    }
    for i, e in enumerate(registry.get("entries", [])):
        if e.get("save_path") == entry["save_path"]:
            registry["entries"][i] = entry
            break
    else:
        registry["entries"].append(entry)
    return entry

def walk_inputs(input_path: str) -> List[str]:
    if os.path.isdir(input_path):
        out = []
        for root, _dirs, files in os.walk(input_path):
            for fn in files:
                if fn.lower().endswith((".melsave", ".zip")):
                    out.append(os.path.join(root, fn))
        return out
    return [input_path]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--registry", required=True)
    args = ap.parse_args()

    reg = load_registry(args.registry)
    if reg.get("env") != TEST_ENV_BANNER:
        print("警告：registry 非 TEST 标记。继续，但别拿它当生产。")

    paths = walk_inputs(args.input)
    if not paths:
        print("没有找到任何 .melsave"); exit(2)

    for p in paths:
        try:
            e = index_one(p, reg)
            print(f"[OK] {p} -> watermark_u64={e['watermark_u64']} length={e['length']}")
        except Exception as ex:
            print(f"[ERR] {p}: {ex}")

    save_registry(args.registry, reg)
    print(f"已写入测试 JSON：{os.path.abspath(args.registry)}，条目数={len(reg.get('entries', []))}")

if __name__ == "__main__":
    main()


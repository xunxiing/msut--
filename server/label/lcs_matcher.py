#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
程序 B：检测指定 .melsave 的水印，并与 registry 进行匹配。

改动：
  - 提取后先做方向规范化：canon(seq) = min(seq, rev(seq))
  - 精确匹配时兼容旧库：对当前存档同时计算 raw、rev(raw)、canon 三种水印去比对
  - LCS 时对双方序列都取 canon，彻底消灭"整段倒序"的影响
"""

import argparse, csv, io, json, os, time, zipfile, re
from typing import Any, List, Optional, Tuple

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
    rev = list(reversed(seq))
    return seq if seq <= rev else rev

def fnv1a64(seq: List[str]) -> int:
    FNV_OFFSET = 14695981039346656037
    FNV_PRIME = 1099511628211
    h = FNV_OFFSET
    for idx, tok in enumerate(seq):
        piece = f"{idx}#{tok}".encode("utf-8", errors="ignore")
        for b in piece:
            h ^= b
            h = (h * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h

# --------- 解析与程序 A 保持一致 ----------
def _extract_seq_from_containers(obj: dict) -> Optional[List[str]]:
    if not isinstance(obj, dict) or "saveObjectContainers" not in obj:
        return None
    rows: List[Tuple[Optional[int], int, str]] = []
    seen = 0
    def collect(node: Any):
        nonlocal seen
        if node is None: return
        if isinstance(node, dict):
            if "objectId" in node:
                oid = str(node.get("objectId"))
                iid = _norm_iid(node.get("instanceId"))
                rows.append((iid, seen, oid)); seen += 1
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
    rows.sort(key=lambda t: (t[0] is None, t[0] if t[0] is not None else 0, t[1]))
    return [oid for (_iid, _idx, oid) in rows]

def _coerce_common(obj: Any) -> Optional[List[str]]:
    def coerce_seq(objs: List[Any]) -> List[str]:
        if not objs: return []
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

def extract_sequence_and_embedded_wm(path: str) -> Tuple[List[str], Optional[int]]:
    embedded = None
    with zipfile.ZipFile(path, "r") as zf:
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

# -------------------- 算法 --------------------
def lcs_length(a: List[str], b: List[str]) -> int:
    if not a or not b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    m = len(b)
    dp = [0]*(m+1)
    for ai in a:
        prev = 0
        for j in range(1, m+1):
            cur = dp[j]
            if ai == b[j-1]:
                dp[j] = prev + 1
            else:
                if dp[j-1] > dp[j]:
                    dp[j] = dp[j-1]
            prev = cur
    return dp[m]

def load_registry(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到 registry：{path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--registry", required=True)
    ap.add_argument("--tolerance", type=float, default=0.10)
    ap.add_argument("--topk", type=int, default=5)
    args = ap.parse_args()

    # 当前存档：原始序列，三种水印
    raw_seq, embedded_wm = extract_sequence_and_embedded_wm(args.input)
    seq_canon = canonicalize([str(x) for x in raw_seq])
    wm_canon = fnv1a64(seq_canon)
    wm_raw   = fnv1a64([str(x) for x in raw_seq])
    wm_rev   = fnv1a64(list(reversed([str(x) for x in raw_seq])))

    reg = load_registry(args.registry)
    entries = reg.get("entries", [])

    # 1) 水印精确匹配（兼容旧库存的 raw 或 rev）
    print("=== 检测结果：水印匹配 ===")
    wm_targets = {wm_canon, wm_raw, wm_rev}
    if embedded_wm is not None:
        wm_targets.add(int(embedded_wm))

    exact_hits = []
    for e in entries:
        try:
            if int(e.get("watermark_u64", -1)) in wm_targets:
                exact_hits.append(e)
        except Exception:
            pass

    if exact_hits:
        for e in exact_hits:
            print(f"[EXACT] 命中 save={e.get('save_name')} path={e.get('save_path')} watermark_u64={e.get('watermark_u64')}")
    else:
        print("未找到精确水印命中。进入 LCS 近似匹配。")

    # 2) LCS 匹配：双方都用 canon(seq)
    print(f"\n=== LCS 近似匹配（容忍度 {args.tolerance:.2f} -> 阈值 S≥{1.0 - args.tolerance:.2f}）===")
    scored = []
    for e in entries:
        e_seq = e.get("sequence")
        if not isinstance(e_seq, list) or not e_seq:
            continue
        e_seq_canon = canonicalize([str(x) for x in e_seq])
        L = lcs_length(seq_canon, e_seq_canon)
        N, M = len(seq_canon), len(e_seq_canon)
        sim_long = L / max(N, M) if max(N, M) else 0.0
        sim_mean = 2 * L / (N + M) if (N + M) else 0.0
        scored.append({"entry": e, "L": L, "N": N, "M": M, "sim_long": sim_long, "sim_mean": sim_mean})
    scored.sort(key=lambda x: (x["sim_long"], x["sim_mean"], x["L"]), reverse=True)
    topk = scored[: max(1, args.topk)]

    threshold = 1.0 - args.tolerance
    any_probable = False
    for s in topk:
        e = s["entry"]
        flag = "PROBABLE_SAME" if s["sim_long"] >= threshold else "different"
        any_probable |= (flag == "PROBABLE_SAME")
        print(f"[{flag}] save={e.get('save_name')} len={s['M']}  L={s['L']}  "
              f"S=L/max(N,M)={s['sim_long']:.4f}  S_mean={s['sim_mean']:.4f}  "
              f"watermark_u64={e.get('watermark_u64')}  path={e.get('save_path')}")

    if not any_probable and not exact_hits:
        print("\n提示：没有达到相似度阈值。你可以：")
        print("  - 提高 --tolerance，比如 0.15 或 0.20")
        print("  - 检查 Data 是否有奇怪的去重/合并，导致顺序特征变弱")

if __name__ == "__main__":
    main()


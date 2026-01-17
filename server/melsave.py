import io
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Optional, Tuple

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response


router = APIRouter()


@dataclass
class GenSource:
    base_dir: Path
    main_path: Path


@dataclass
class MelsaveResult:
    filename: str
    data: bytes


def _find_generator_dir() -> Optional[GenSource]:
    base = Path(__file__).resolve().parent
    # Prefer folder that ends with the known version marker and contains main.py
    for d in base.iterdir():
        if d.is_dir() and (d / "main.py").exists() and "v2.3.11" in d.name:
            return GenSource(base_dir=d, main_path=d / "main.py")
    # Fallback: any subdir that has converter + main
    for d in base.iterdir():
        if d.is_dir() and (d / "main.py").exists() and (d / "converter_v2.py").exists():
            return GenSource(base_dir=d, main_path=d / "main.py")
    return None


def _copy_tree(src: Path, dst: Path) -> None:
    # Copy generator folder to an isolated temp dir to avoid race conditions.
    # Skip caches and existing sample outputs to keep it lighter.
    def _ignore(_dir: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for n in names:
            if n in {".git", "__pycache__", "output"}:
                ignored.add(n)
            if n.endswith(".melsave"):
                ignored.add(n)
        return ignored

    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)
    # Normalize expected filenames for Linux case-sensitivity
    # The pipeline expects lowercase 'data.json'. If the source ships 'Data.json', rename it.
    up = dst / "Data.json"
    low = dst / "data.json"
    try:
        if up.exists() and not low.exists():
            up.rename(low)
    except Exception:
        # not fatal; the pipeline will error clearly if missing
        pass

    # Clear stale artifacts that could confuse runs
    for name in ("graph.json", "output.json", "data_after_modify.json", "ungraph.json"):
        try:
            p = dst / name
            if p.exists():
                p.unlink()
        except Exception:
            pass

    try:
        out_dir = dst / "output"
        if out_dir.exists():
            shutil.rmtree(out_dir, ignore_errors=True)
    except Exception:
        pass


def _run_pipeline(temp_dir: Path) -> Path:
    # Prefer running in a subprocess to isolate execution of DSL code.
    import subprocess
    start_ts = time.time()
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    try:
        subprocess.run(
            [sys.executable, "main.py"],
            cwd=str(temp_dir),
            env=env,
            check=True,
            timeout=60,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        stdout = (e.stdout or b"").decode("utf-8", "ignore")
        stderr = (e.stderr or b"").decode("utf-8", "ignore")
        raise RuntimeError(f"子进程执行失败: {stderr or stdout}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("生成超时")

    # Pick the most recent .melsave (output path may vary in newer generators).
    melsaves = sorted(temp_dir.rglob("*.melsave"), key=lambda p: p.stat().st_mtime, reverse=True)
    fresh = [p for p in melsaves if p.stat().st_mtime >= start_ts - 1.0]
    if fresh:
        return fresh[0]
    if not melsaves:
        raise RuntimeError("未生成 .melsave 文件")
    return melsaves[0]


def _encode_filename_header(filename: str) -> str:
    from urllib.parse import quote
    return f"attachment; filename*=UTF-8''{quote(filename)}"


def generate_melsave_bytes(dsl_code: str) -> MelsaveResult:
    """Run the generator pipeline and return the produced .melsave bytes."""
    if not isinstance(dsl_code, str) or not dsl_code.strip():
        raise ValueError("DSL 内容不能为空")

    src = _find_generator_dir()
    if not src:
        raise RuntimeError("找不到生成器目录")

    base_tmp = Path(tempfile.mkdtemp(prefix="melsave_", dir=str(Path(__file__).resolve().parent)))
    try:
        _copy_tree(src.base_dir, base_tmp)
        (base_tmp / "input.py").write_text(dsl_code, encoding="utf-8")
        out_path = _run_pipeline(base_tmp)
        data = out_path.read_bytes()
        return MelsaveResult(filename=out_path.name, data=data)
    finally:
        try:
            shutil.rmtree(base_tmp, ignore_errors=True)
        except Exception:
            pass


@router.post("/api/melsave/generate")
def generate_melsave(body: dict):
    # Accept body with { dsl: string }
    dsl_code = body.get("dsl") if isinstance(body, dict) else None
    try:
        result = generate_melsave_bytes(dsl_code)
        headers = {
            "Content-Disposition": _encode_filename_header(result.filename)
        }
        return Response(content=result.data, media_type="application/octet-stream", headers=headers)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"生成失败: {e}"})

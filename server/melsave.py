import io
import os
import shutil
import sys
import tempfile
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
            if n in {".git", "__pycache__"}:
                ignored.add(n)
            if n.endswith(".melsave"):
                ignored.add(n)
        return ignored

    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)


def _run_pipeline(temp_dir: Path) -> Path:
    # Prefer running in a subprocess to isolate execution of DSL code.
    import subprocess
    env = {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    }
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

    # Pick the most recent .melsave
    melsaves = sorted(temp_dir.glob("*.melsave"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not melsaves:
        raise RuntimeError("未生成 .melsave 文件")
    return melsaves[0]


def _encode_filename_header(filename: str) -> str:
    from urllib.parse import quote
    return f"attachment; filename*=UTF-8''{quote(filename)}"


@router.post("/api/melsave/generate")
def generate_melsave(body: dict):
    # Accept body with { dsl: string }
    dsl_code = body.get("dsl") if isinstance(body, dict) else None
    if not isinstance(dsl_code, str) or not dsl_code.strip():
        return JSONResponse(status_code=400, content={"error": "DSL 内容不能为空"})

    src = _find_generator_dir()
    if not src:
        return JSONResponse(status_code=500, content={"error": "找不到生成器目录"})

    # Create isolated working dir
    base_tmp = Path(tempfile.mkdtemp(prefix="melsave_", dir=str(Path(__file__).resolve().parent)))
    try:
        _copy_tree(src.base_dir, base_tmp)
        # Write DSL to input.py expected by the pipeline
        (base_tmp / "input.py").write_text(dsl_code, encoding="utf-8")

        # Run the pipeline
        out_path = _run_pipeline(base_tmp)

        # Load bytes and respond for download
        data = out_path.read_bytes()
        headers = {
            "Content-Disposition": _encode_filename_header(out_path.name)
        }
    return Response(content=data, media_type="application/octet-stream", headers=headers)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"生成失败: {e}"})
    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(base_tmp, ignore_errors=True)
        except Exception:
            pass

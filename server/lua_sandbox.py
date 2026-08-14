"""
MelonLuaSandbox API routes.

Exposes the melon-lua SDK (Lua chip execution, catalog, melsave builder)
as HTTP endpoints under /api/lua.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import traceback
from typing import Any, Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/lua", tags=["lua-sandbox"])

# ------------------------------------------------------------------ #
# Lazy imports — melon_lua is heavy (lupa + Box2D); avoid import at    #
# module load time so the server starts even if deps are missing.     #
# ------------------------------------------------------------------ #
_runner_mod = None
_world_mod = None
_session_mod = None
_builder_mod = None
_ui_mod = None
_catalog_mod = None


def _ensure_imports():
    global _runner_mod, _world_mod, _session_mod, _builder_mod, _ui_mod, _catalog_mod
    if _runner_mod is None:
        from melon_lua import (
            MelonScriptRunner,
            WorldContext,
            MelsaveSession,
            MelsaveBuilder,
            UIControllerBuilder,
            element_schema,
            list_spawnables,
            get_profile_by_object_id,
            object_id_for_name,
            list_item_gates,
            catalog_stats,
        )
        _runner_mod = MelonScriptRunner
        _world_mod = WorldContext
        _session_mod = MelsaveSession
        _builder_mod = MelsaveBuilder
        _ui_mod = UIControllerBuilder
        _catalog_mod = {
            "element_schema": element_schema,
            "list_spawnables": list_spawnables,
            "get_profile_by_object_id": get_profile_by_object_id,
            "object_id_for_name": object_id_for_name,
            "list_item_gates": list_item_gates,
            "catalog_stats": catalog_stats,
        }


# ------------------------------------------------------------------ #
# Request / response models                                           #
# ------------------------------------------------------------------ #


class RunRequest(BaseModel):
    source: str = Field(..., description="Lua 芯片源码")
    ticks: int = Field(1, ge=1, le=100000, description="运行 tick 数")
    tps: int = Field(20, ge=1, le=120, description="Ticks per second")
    inputs: Optional[dict] = Field(None, description="静态输入 {num: {...}, string: {...}}")
    seed_entities: Optional[list[str]] = Field(
        None,
        description='种子实体列表 ["crate,0,10", "floor,0,0"]',
    )
    seed_static: Optional[list[str]] = Field(None, description="静态种子实体")
    quiet: bool = Field(True, description="静默模式（不打印到 stdout）")


class DebugRequest(BaseModel):
    source: str = Field(..., description="Lua 芯片源码")
    ticks: int = Field(1, ge=1, le=10000, description="运行 tick 数")
    tps: int = Field(20, ge=1, le=120)
    inputs: Optional[dict] = None
    stop_on_error: bool = True


class MelsaveBuildRequest(BaseModel):
    items: list[dict] = Field(
        default_factory=list,
        description='[{"object_id": 202, "x": 0, "y": 1, "color": [0,1,0.3,1], "dynamic": true}]',
    )
    chips: list[dict] = Field(
        default_factory=list,
        description='[{"source": "lua code", "x": 0, "y": 0, "inputs": [...], "outputs": [...], "variables": [...], "tps": 30, "title": "..."}]',
    )
    connections: list[dict] = Field(
        default_factory=list,
        description='[{"source_idx": 0, "output_gate": "entity", "target_idx": 1, "input_gate": "target"}]',
    )
    meta: Optional[dict] = Field(None, description="覆盖 MetaData 字段")


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #


@router.get("/catalog")
def get_catalog(
    q: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(100, ge=1, le=500),
):
    """获取可生成物品目录。"""
    _ensure_imports()
    names = _catalog_mod["list_spawnables"]()
    stats = _catalog_mod["catalog_stats"]()
    if q:
        q_lower = q.lower()
        names = [n for n in names if q_lower in n.lower()]
    return {"total": stats, "items": names[:limit]}


@router.get("/catalog/{object_id}")
def get_profile(object_id: str):
    """按 objectId 或名称获取物体 profile（尺寸、质量、贴图等）。"""
    _ensure_imports()
    oid = None
    try:
        oid = int(object_id)
    except ValueError:
        oid = _catalog_mod["object_id_for_name"](object_id)
    if oid is None:
        return JSONResponse(status_code=404, content={"error": "未找到该物体"})
    prof = _catalog_mod["get_profile_by_object_id"](oid)
    if prof is None:
        return JSONResponse(status_code=404, content={"error": "未找到该物体的 profile"})
    if isinstance(prof, dict):
        return prof
    if hasattr(prof, "__dict__"):
        return {k: v for k, v in vars(prof).items() if not k.startswith("_")}
    return JSONResponse(status_code=500, content={"error": "无法序列化 profile"})


@router.get("/gates/{object_id}")
def get_gates(object_id: str):
    """查询物体的输入/输出门（门名 + 类型）。"""
    _ensure_imports()
    gates = _catalog_mod["list_item_gates"](object_id)
    if gates is None:
        return JSONResponse(status_code=404, content={"error": "未找到该物体的门信息"})
    if isinstance(gates, dict):
        return gates
    return JSONResponse(status_code=500, content={"error": "无法序列化门信息"})


@router.get("/elements")
def list_elements():
    """列出所有 UI 元素类型及其输出门。"""
    _ensure_imports()
    schema = _catalog_mod["element_schema"]()
    return schema


@router.get("/elements/{type_name}")
def get_element_schema(type_name: str):
    """查询指定 UI 元素类型的完整 schema（输入门/输出门/默认值/工厂签名）。"""
    _ensure_imports()
    schema = _catalog_mod["element_schema"](type_name)
    if schema is None:
        return JSONResponse(status_code=404, content={"error": f"未知元素类型: {type_name}"})
    return schema


@router.post("/run")
def run_chip(req: RunRequest):
    """运行 Lua 芯片，返回最终 outputs 和日志。"""
    _ensure_imports()
    try:
        world = _world_mod(seed=42)
        if req.seed_entities:
            for spec in req.seed_entities:
                parts = spec.split(",")
                name = parts[0]
                x = float(parts[1]) if len(parts) > 1 else 0
                y = float(parts[2]) if len(parts) > 2 else 0
                world.spawn_entity(name, x, y, dynamic=True)
        if req.seed_static:
            for spec in req.seed_static:
                parts = spec.split(",")
                name = parts[0]
                x = float(parts[1]) if len(parts) > 1 else 0
                y = float(parts[2]) if len(parts) > 2 else 0
                world.spawn_entity(name, x, y, dynamic=False)

        runner = _runner_mod(tps=req.tps, world=world, quiet=req.quiet)
        ok = runner.compile(req.source, chunk_name="@api_chip.lua")
        if not ok:
            return JSONResponse(
                status_code=400,
                content={"error": f"编译失败: {runner.last_error}"},
            )

        runner.call_on_init()
        runner.run_loop(ticks=req.ticks, inputs=req.inputs)

        outputs = runner.get_outputs()
        logs = runner.logs if hasattr(runner, "logs") else []
        error = runner.last_error

        entities = []
        if hasattr(world, "entities"):
            for eid, ent in world.entities.items():
                entities.append(
                    {
                        "id": eid,
                        "position_x": getattr(ent, "position_x", 0),
                        "position_y": getattr(ent, "position_y", 0),
                    }
                )

        return {
            "outputs": outputs,
            "logs": logs[-200:] if len(logs) > 200 else logs,
            "error": error,
            "entity_count": len(entities),
            "entities": entities[:50],
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "trace": traceback.format_exc()},
        )


@router.post("/debug")
def debug_run(req: DebugRequest):
    """调试运行 Lua 芯片，返回每 tick 的轨迹（outputs + logs_delta）。"""
    _ensure_imports()
    try:
        world = _world_mod(seed=42)
        runner = _runner_mod(tps=req.tps, world=world, quiet=True)
        ok = runner.compile(req.source, chunk_name="@api_debug.lua")
        if not ok:
            return JSONResponse(
                status_code=400,
                content={"error": f"编译失败: {runner.last_error}"},
            )
        runner.call_on_init()
        result = runner.run_ticks(
            req.ticks,
            inputs=req.inputs,
            stop_on_error=req.stop_on_error,
        )
        if isinstance(result, dict):
            return result
        return {"result": str(result)}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "trace": traceback.format_exc()},
        )


@router.post("/melsave/build")
def build_melsave(req: MelsaveBuildRequest):
    """从零构建 .melsave 文件，返回文件流。"""
    _ensure_imports()
    try:
        b = _builder_mod()
        for item in req.items:
            b.add_item(
                item["object_id"],
                x=item.get("x", 0),
                y=item.get("y", 0),
                color=tuple(item["color"]) if item.get("color") else None,
                dynamic=item.get("dynamic", True),
                scale_x=item.get("scale_x", 1.0),
                scale_y=item.get("scale_y", 1.0),
            )
        for chip in req.chips:
            b.add_lua_chip(
                chip["source"],
                x=chip.get("x", 0),
                y=chip.get("y", 0),
                inputs=chip.get("inputs", []),
                outputs=chip.get("outputs", []),
                variables=chip.get("variables", []),
                tps=chip.get("tps", 30),
                title=chip.get("title", ""),
            )
        for conn in req.connections:
            b.connect(
                conn["source_idx"],
                conn["output_gate"],
                conn["target_idx"],
                conn["input_gate"],
                name=conn.get("name", ""),
            )
        if req.meta:
            b.set_meta(**req.meta)

        with tempfile.NamedTemporaryFile(suffix=".melsave", delete=False) as tmp:
            tmp_path = b.save(tmp.name, write_icon=True)

        with open(tmp_path, "rb") as f:
            content = f.read()
        os.unlink(tmp_path)

        filename = "build.melsave"
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "trace": traceback.format_exc()},
        )

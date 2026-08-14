# Lua Sandbox API 文档

基于 [MelonLuaSandbox](https://github.com/xunxiing/MelonLuaSandbox) 项目，提供甜瓜游乐场 Lua 芯片在线执行、调试、存档构建等能力。

## 基础信息

- **API 前缀**：`/api/lua`
- **认证**：无需认证（匿名访问）
- **响应格式**：JSON（除文件流接口外）
- **字符编码**：UTF-8

---

## 1. 获取可生成物品目录

获取甜瓜游乐场中所有可生成物品的名称列表。

### 请求

```
GET /api/lua/catalog
```

**查询参数**

| 参数 | 类型 | 必需 | 默认 | 说明 |
|------|------|------|------|------|
| `q` | string | 否 | — | 搜索关键词（模糊匹配物品名称） |
| `limit` | int | 否 | 100 | 返回数量上限（最大 500） |

### 请求示例

```bash
# 获取全部可生成物品
GET /api/lua/catalog?limit=50

# 搜索包含 "plastic" 的物品
GET /api/lua/catalog?q=plastic
```

### 成功响应

```json
{
  "total": {"total": 456, "with_physics": 245},
  "items": ["ResizablePlastic", "Box", "Human", "Engine", "..."]
}
```

---

## 2. 获取物体 Profile

按 objectId 或名称获取物体的物理 profile（尺寸、质量、贴图等）。

### 请求

```
GET /api/lua/catalog/{object_id}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `object_id` | string | objectId（如 `202`）或物品名称（如 `ResizablePlastic`） |

### 请求示例

```bash
GET /api/lua/catalog/202
GET /api/lua/catalog/ResizablePlastic
```

### 成功响应

```json
{
  "objectId": 202,
  "name": "ResizablePlastic",
  "width": 1.0,
  "height": 1.0,
  "mass": 1.0,
  "sprite": "..."
}
```

### 错误响应

```json
{"error": "未找到该物体"}
```

---

## 3. 查询物体输入/输出门

获取物体的输入门和输出门信息（门名、类型）。

### 请求

```
GET /api/lua/gates/{object_id}
```

### 请求示例

```bash
GET /api/lua/gates/261      # 文字屏
GET /api/lua/gates/文字屏
```

### 成功响应

```json
{
  "inputs": [
    {"key": "activation", "data_name": "activation", "data_type": 2},
    {"key": "string", "data_name": "text", "data_type": 4}
  ],
  "outputs": [
    {"key": "entity", "data_name": "entity", "data_type": 1},
    {"key": "activation", "data_name": "activation", "data_type": 2},
    {"key": "text", "data_name": "text", "data_type": 4}
  ]
}
```

---

## 4. 列出所有 UI 元素类型

获取所有可用的 UI 控制器元素类型及其输出门。

### 请求

```
GET /api/lua/elements
```

### 成功响应

```json
{
  "available_types": [
    {"type": "button", "outputs": ["Button is down", "Button is up"]},
    {"type": "slider", "outputs": ["Value"]},
    {"type": "joystick", "outputs": ["Joystick Activation", "Joystick Direction", "Joystick Angle"]}
  ]
}
```

---

## 5. 查询 UI 元素 Schema

获取指定 UI 元素类型的完整 schema（输入门、输出门、默认值、工厂签名）。

### 请求

```
GET /api/lua/elements/{type_name}
```

### 请求示例

```bash
GET /api/lua/elements/button
GET /api/lua/elements/slider
GET /api/lua/elements/joy    # 前缀匹配
```

### 成功响应

```json
{
  "type": "slider",
  "type_ids": [5, 6, 7],
  "description": "滑块，拖动改变 Value 输出",
  "inputs": [
    {"key": "Target value", "type": "number", "default": 0.0, "hint": "滑块目标值"},
    {"key": "Min Value", "type": "number", "default": -1.0, "hint": "滑块最小值"}
  ],
  "outputs": [
    {"key": "Value", "type": "number", "default": 1.0, "hint": "当前值"}
  ],
  "factory": "UIElement.slider(name, x, y, value=0, mn=0, mx=1, integers_only=False)"
}
```

---

## 6. 运行 Lua 芯片

编译并运行 Lua 芯片，返回最终 outputs、日志和实体快照。

### 请求

```
POST /api/lua/run
Content-Type: application/json
```

**请求体**

| 字段 | 类型 | 必需 | 默认 | 说明 |
|------|------|------|------|------|
| `source` | string | 是 | — | Lua 芯片源码 |
| `ticks` | int | 否 | 1 | 运行 tick 数（1-100000） |
| `tps` | int | 否 | 20 | Ticks per second（1-120） |
| `inputs` | object | 否 | null | 静态输入，格式见下方 |
| `seed_entities` | string[] | 否 | null | 种子动态实体，格式 `"name,x,y"` |
| `seed_static` | string[] | 否 | null | 种子静态实体，格式 `"name,x,y"` |
| `quiet` | bool | 否 | true | 静默模式 |

**输入格式**

```json
{
  "num": {"a": 5, "b": 3},
  "string": {"mode": "attack"},
  "vec": {"dir": {"x": 1, "y": 0, "z": 0, "w": 0}}
}
```

### 请求示例

```bash
curl -X POST http://localhost:3000/api/lua/run \
  -H "Content-Type: application/json" \
  -d '{
    "source": "function OnInit() print(\"hello\") end\nfunction OnTick() outputs.num.x = 42 end",
    "ticks": 10
  }'
```

### 成功响应

```json
{
  "outputs": {
    "num": {"x": 42.0},
    "string": {},
    "vec": {},
    "color": {}
  },
  "logs": [{"type": "print", "message": "hello"}],
  "error": null,
  "entity_count": 0,
  "entities": []
}
```

### 编译错误

```json
{"error": "编译失败: [string \"@api_chip.lua\"]:3: unexpected symbol near ')'"}
```

---

## 7. 调试运行 Lua 芯片

编译并运行 Lua 芯片，返回每 tick 的完整轨迹（outputs + 日志增量 + 变量）。

### 请求

```
POST /api/lua/debug
Content-Type: application/json
```

**请求体**

| 字段 | 类型 | 必需 | 默认 | 说明 |
|------|------|------|------|------|
| `source` | string | 是 | — | Lua 芯片源码 |
| `ticks` | int | 否 | 1 | 运行 tick 数（1-10000） |
| `tps` | int | 否 | 20 | Ticks per second |
| `inputs` | object | 否 | null | 静态输入 |
| `stop_on_error` | bool | 否 | true | 出错时停止 |

### 请求示例

```bash
curl -X POST http://localhost:3000/api/lua/debug \
  -H "Content-Type: application/json" \
  -d '{
    "source": "function OnTick() outputs.num.tick = inputs.num.a * 2 end",
    "ticks": 5,
    "inputs": {"num": {"a": 10}}
  }'
```

### 成功响应

```json
{
  "error": null,
  "outputs": {"num": {"tick": 20.0}},
  "frames": [
    {
      "tick": 0,
      "outputs": {"num": {"tick": 20.0}},
      "logs_delta": [],
      "error": null,
      "variables": {},
      "entity_count": 0
    }
  ],
  "logs": []
}
```

---

## 8. 构建 .melsave 存档

从零构建甜瓜游乐场存档文件，返回 `.melsave` 文件流。

### 请求

```
POST /api/lua/melsave/build
Content-Type: application/json
```

**请求体**

| 字段 | 类型 | 必需 | 默认 | 说明 |
|------|------|------|------|------|
| `items` | object[] | 否 | [] | 物品列表 |
| `chips` | object[] | 否 | [] | Lua 芯片列表 |
| `connections` | object[] | 否 | [] | 门连线列表 |
| `meta` | object | 否 | null | 覆盖 MetaData 字段 |

**items 元素**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `object_id` | int | 是 | 甜瓜 objectId（如 202=塑料板） |
| `x` | float | 否 | x 坐标（默认 0） |
| `y` | float | 否 | y 坐标（默认 0） |
| `color` | float[4] | 否 | RGBA 颜色（0-1） |
| `dynamic` | bool | 否 | 是否为动态刚体（默认 true） |
| `scale_x` | float | 否 | x 缩放（默认 1.0） |
| `scale_y` | float | 否 | y 缩放（默认 1.0） |

**chips 元素**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `source` | string | 是 | Lua 芯片源码 |
| `x` | float | 否 | x 坐标 |
| `y` | float | 否 | y 坐标 |
| `inputs` | object[] | 否 | 输入门列表 `[{"name":"target","type":"entity"}]` |
| `outputs` | object[] | 否 | 输出门列表 `[{"name":"out","type":"number"}]` |
| `variables` | object[] | 否 | 持久变量 `[{"name":"count","value":0}]` |
| `tps` | int | 否 | Ticks per second（默认 30） |
| `title` | string | 否 | 芯片标题 |

**Gate 类型别名**

| 别名 | 说明 |
|------|------|
| `entity` | 实体引用 |
| `number` / `num` | 浮点数 |
| `int` / `integer` | 整数 |
| `string` / `str` | 字符串 |
| `vector` / `vec` | 向量 |
| `array_entity` | 实体数组 |
| `array_num` | 数值数组 |
| `array_string` | 字符串数组 |
| `array_vec` | 向量数组 |

**connections 元素**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `source_idx` | int | 是 | 源容器索引（add_item/add_lua_chip 的返回值） |
| `output_gate` | string | 是 | 源输出门名（Key 或 DataName） |
| `target_idx` | int | 是 | 目标容器索引 |
| `input_gate` | string | 是 | 目标输入门名 |
| `name` | string | 否 | 连线名称 |

### 请求示例

```bash
curl -X POST http://localhost:3000/api/lua/melsave/build \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"object_id": 202, "x": 0.5, "y": 0.03, "color": [0, 1, 0.3, 1]}
    ],
    "chips": [
      {
        "source": "function OnInit() print(\"chip started\") end\nfunction OnTick() local e = Entity(1) local x, y = e:getPosition() outputs.num.x = x outputs.num.y = y end",
        "x": -0.5, "y": -0.03,
        "inputs": [{"name": "target", "type": "entity"}],
        "outputs": [{"name": "tick", "type": "number"}, {"name": "status", "type": "string"}],
        "tps": 30
      }
    ],
    "connections": [
      {"source_idx": 0, "output_gate": "entity", "target_idx": 1, "input_gate": "target"}
    ]
  }' \
  -o build.melsave
```

### 成功响应

- **Content-Type**: `application/octet-stream`
- **Content-Disposition**: `attachment; filename*=UTF-8''build.melsave`
- **Body**: `.melsave` ZIP 文件二进制流

### 错误响应

```json
{"error": "objectId 999 not found in catalog", "trace": "..."}
```

---

## Lua 芯片生命周期

芯片源码可定义以下函数（均为可选）：

```lua
function OnInit() end          -- 芯片初始化，调用一次
function OnActivated() end     -- 激活时调用一次
function OnTick() end           -- 每 tick 调用（按 TPS）
function OnDeactivated() end   -- 停用时调用一次
function OnDestroy() end        -- 销毁时调用一次
function OnSpawned(requestId, entities) end  -- spawn.create 完成后回调
```

## 类型化输入输出

```lua
function OnTick()
    -- 读取输入
    local speed = inputs.num.speed or 0
    local mode = inputs.string.mode or "idle"
    local dir = inputs.vec.dir  -- {x=, y=, z=, w=}

    -- Entity OOP
    local e = Entity(1)
    e:setVelocity(speed, 0)
    local x, y = e:getPosition()

    -- 写入输出
    outputs.num.x = x
    outputs.num.y = y
    outputs.string.status = "running"

    -- 生成请求
    spawn.create("human", x + 2, y)
end
```

## 可用 API 模块

| 模块 | 说明 |
|------|------|
| `entity` | 实体操作（位置、速度、力、冻结等） |
| `spawn` | 生成实体 |
| `env` | 环境信息 |
| `camera` | 摄像机控制 |
| `input` | 输入读取 |
| `inputFilter` | 输入过滤 |
| `chip` | 芯片自身信息 |
| `mechanic` | 机械操作 |
| `world` | 世界操作 |
| `variables` | 持久变量 |
| `uicontrol` | UI 控制器交互 |
| `print` | 日志输出 |

## 限制

- 物理使用 Box2D 2D 模拟，物体形状均为矩形
- 渲染、音效、网络、真实输入设备无法模拟
- `mechanic`、`uicontrol`、`inputFilter` 等模块在沙盒中返回 mock 值
- 无真实时间等待，适合快速批量 tick 模拟

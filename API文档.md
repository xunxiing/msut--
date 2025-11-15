# MSUT 主站 API 文档

## 概述

MSUT 主站是一个基于 FastAPI 构建的文件共享和资源管理平台，提供用户认证、资源上传、文件管理和水印检测等功能。

## 基础信息

- 基础URL: `http://127.0.0.1:5173` (默认)
- 认证方式: Cookie-based JWT
- 文件上传大小限制: 50MB

## API 端点

### 认证相关

#### 用户注册

- **路径**: `POST /api/auth/register`
- **描述**: 注册新用户
- **请求体**:
  ```json
  {
    "username": "string (3-32字符)",
    "password": "string (6-72字符)",
    "name": "string (1-32字符)"
  }
  ```
- **响应**:
  ```json
  {
    "user": {
      "id": "number",
      "username": "string",
      "name": "string"
    }
  }
  ```
- **错误响应**:
  - 409: 用户名已注册

#### 用户登录

- **路径**: `POST /api/auth/login`
- **描述**: 用户登录
- **请求体**:
  ```json
  {
    "username": "string (3-32字符)",
    "password": "string (6-72字符)"
  }
  ```
- **响应**:
  ```json
  {
    "user": {
      "id": "number",
      "username": "string",
      "name": "string"
    }
  }
  ```
- **错误响应**:
  - 401: 用户名或密码错误

#### 用户登出

- **路径**: `POST /api/auth/logout`
- **描述**: 用户登出
- **响应**:
  ```json
  {
    "ok": true
  }
  ```

#### 获取当前用户信息

- **路径**: `GET /api/auth/me`
- **描述**: 获取当前登录用户的信息
- **响应**:
  ```json
  {
    "user": {
      "id": "number",
      "username": "string",
      "name": "string"
    }
  }
  ```
- **注意**: 未登录时返回 `{"user": null}`

### 资源管理

#### 创建资源

- **路径**: `POST /api/resources`
- **描述**: 创建新资源
- **请求体**:
  ```json
  {
    "title": "string (必填)",
    "description": "string (可选)",
    "usage": "string (可选)"
  }
  ```
- **响应**:
  ```json
  {
    "id": "number",
    "slug": "string",
    "title": "string",
    "description": "string",
    "usage": "string",
    "shareUrl": "string"
  }
  ```
- **错误响应**:
  - 400: 标题必填
  - 401: 未登录

#### 更新资源

- **路径**: `PATCH /api/resources/{rid}`
- **描述**: 更新资源信息
- **请求体**:
  ```json
  {
    "description": "string (可选)",
    "usage": "string (可选)"
  }
  ```
- **响应**:
  ```json
  {
    "id": "number",
    "slug": "string",
    "title": "string",
    "description": "string",
    "usage": "string",
    "created_at": "string",
    "shareUrl": "string"
  }
  ```
- **错误响应**:
  - 400: 没有需要更新的字段
  - 401: 未登录
  - 403: 无法操作其他用户的资源
  - 404: 资源不存在

#### 删除资源

- **路径**: `DELETE /api/resources/{rid}`
- **描述**: 删除资源及其关联文件
- **响应**:
  ```json
  {
    "ok": true
  }
  ```
- **错误响应**:
  - 401: 未登录
  - 403: 无法操作其他用户的资源
  - 404: 资源不存在

#### 获取资源详情

- **路径**: `GET /api/resources/{slug}`
- **描述**: 根据slug获取资源详情
- **响应**:
  ```json
  {
    "id": "number",
    "slug": "string",
    "title": "string",
    "description": "string",
    "usage": "string",
    "created_at": "string",
    "author_name": "string",
    "author_username": "string",
    "files": [
      {
        "id": "number",
        "original_name": "string",
        "stored_name": "string",
        "mime": "string",
        "size": "number",
        "url_path": "string",
        "created_at": "string"
      }
    ],
    "shareUrl": "string"
  }
  ```
- **错误响应**:
  - 404: 未找到资源

#### 资源列表

- **路径**: `GET /api/resources`
- **描述**: 获取资源列表
- **查询参数**:
  - `q`: 搜索关键词 (可选)
  - `page`: 页码 (默认1)
  - `pageSize`: 每页数量 (默认12, 最大50)
- **响应**:
  ```json
  {
    "items": [
      {
        "id": "number",
        "slug": "string",
        "title": "string",
        "description": "string",
        "created_at": "string",
        "author_name": "string",
        "author_username": "string"
      }
    ],
    "page": "number",
    "pageSize": "number",
    "total": "number"
  }
  ```

#### 获取我的资源列表

- **路径**: `GET /api/my/resources`
- **描述**: 获取当前用户的资源列表
- **响应**:
  ```json
  {
    "items": [
      {
        "id": "number",
        "slug": "string",
        "title": "string",
        "description": "string",
        "usage": "string",
        "created_at": "string",
        "files": [
          {
            "id": "number",
            "original_name": "string",
            "stored_name": "string",
            "mime": "string",
            "size": "number",
            "url_path": "string",
            "created_at": "string"
          }
        ],
        "shareUrl": "string"
      }
    ]
  }
  ```
- **错误响应**:
  - 401: 未登录

### 文件管理

#### 上传文件

- **路径**: `POST /api/files/upload`
- **描述**: 向资源上传文件
- **请求体**:
  - `resourceId`: 资源ID (必填)
  - `files`: 文件列表 (必填)
  - `saveWatermark`: 是否保存水印 (可选)
- **响应**:
  ```json
  {
    "ok": true,
    "files": [
      {
        "id": "number",
        "originalName": "string",
        "size": "number",
        "mime": "string",
        "urlPath": "string"
      }
    ]
  }
  ```
- **错误响应**:
  - 400: 没有文件或上传失败
  - 401: 未登录
  - 403: 无法操作其他用户的资源
  - 404: 资源不存在

#### 下载文件

- **路径**: `GET /api/files/{fid}/download`
- **描述**: 下载文件
- **响应**: 文件二进制内容
- **错误响应**:
  - 404: 文件不存在或文件丢失

### 水印检测

#### 检查水印

- **路径**: `POST /api/watermark/check`
- **描述**: 检查.melsave或.zip文件的水印
- **请求体**: 文件 (仅支持.melsave或.zip)
- **响应**:
  ```json
  {
    "watermark": "number",
    "length": "number",
    "embedded": "number",
    "matches": [
      {
        "fileId": "number",
        "resourceId": "number",
        "resourceSlug": "string",
        "resourceTitle": "string",
        "originalName": "string",
        "urlPath": "string"
      }
    ]
  }
  ```
- **错误响应**:
  - 400: 仅支持.melsave或.zip文件或提取失败

### Melsave生成

#### 生成Melsave文件

- **路径**: `POST /api/melsave/generate`
- **描述**: 根据DSL代码生成.melsave文件
- **请求体**:
  ```json
  {
    "dsl": "string"
  }
  ```
- **响应**: .melsave文件的二进制内容
- **错误响应**:
  - 400: DSL内容不能为空
  - 500: 找不到生成器目录或生成失败

### 点赞功能

#### 资源点赞

- **路径**: `POST /api/resources/{rid}/like`
- **描述**: 点赞资源
- **响应**:
  ```json
  {
    "liked": true,
    "likes": "number"
  }
  ```
- **错误响应**:
  - 401: 未登录
  - 404: 资源不存在

#### 取消资源点赞

- **路径**: `DELETE /api/resources/{rid}/like`
- **描述**: 取消资源点赞
- **响应**:
  ```json
  {
    "liked": false,
    "likes": "number"
  }
  ```
- **错误响应**:
  - 401: 未登录
  - 404: 资源不存在

#### 获取资源点赞信息

- **路径**: `GET /api/resources/likes`
- **描述**: 获取多个资源的点赞信息
- **查询参数**:
  - `ids`: 资源ID列表，逗号分隔
- **响应**:
  ```json
  {
    "items": [
      {
        "id": "number",
        "likes": "number",
        "liked": "boolean"
      }
    ]
  }
  ```
- **错误响应**:
  - 400: 参数错误

#### 文件点赞

- **路径**: `POST /api/files/{fid}/like`
- **描述**: 点赞文件
- **响应**:
  ```json
  {
    "liked": true,
    "likes": "number"
  }
  ```
- **错误响应**:
  - 401: 未登录
  - 404: 文件不存在

#### 取消文件点赞

- **路径**: `DELETE /api/files/{fid}/like`
- **描述**: 取消文件点赞
- **响应**:
  ```json
  {
    "liked": false,
    "likes": "number"
  }
  ```
- **错误响应**:
  - 401: 未登录
  - 404: 文件不存在

#### 获取文件点赞信息

- **路径**: `GET /api/files/likes`
- **描述**: 获取多个文件的点赞信息
- **查询参数**:
  - `ids`: 文件ID列表，逗号分隔
- **响应**:
  ```json
  {
    "items": [
      {
        "id": "number",
        "likes": "number",
        "liked": "boolean"
      }
    ]
  }
  ```
- **错误响应**:
  - 400: 参数错误

### 系统接口

#### 健康检查

- **路径**: `GET /`
- **描述**: 系统健康检查
- **响应**:
  ```json
  {
    "ok": true
  }
  ```

#### 私有Ping

- **路径**: `GET /api/private/ping`
- **描述**: 私有Ping接口，需要登录
- **响应**:
  ```json
  {
    "pong": true
  }
  ```
- **错误响应**:
  - 401: 未登录

## 静态文件

- **路径**: `/uploads/*`
- **描述**: 访问上传的静态文件
- **注意**: 文件存储在服务器`uploads`目录下

## 错误处理

所有API在出错时都会返回适当的HTTP状态码和错误信息，通常格式如下：

```json
{
  "error": "错误描述"
}
```

## 认证

系统使用基于Cookie的JWT认证。登录成功后，服务器会在响应中设置包含JWT令牌的Cookie。后续请求会自动携带此Cookie进行身份验证。

## 数据库

系统使用SQLite数据库存储用户、资源、文件和点赞信息。数据库文件位于`data/data.sqlite`。

## 文件上传

- 文件上传大小限制: 50MB
- 支持多文件同时上传
- 上传的文件存储在服务器`uploads`目录下
- 对于.melsave和.zip文件，可以选择保存水印信息

## 水印系统

系统支持对.melsave和.zip文件进行水印提取和比对，可以检测文件是否来源于已上传的文件。

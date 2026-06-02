---
module: routing
title: FastAPI 路由设计约定
tags: [routing, router, api-design]
---

# 路由设计约定

## APIRouter 模块化

使用 `APIRouter` 拆分大型 API 为独立路由模块，每个模块负责一个业务域：

```python
from fastapi import APIRouter

router = APIRouter(prefix="/items", tags=["items"])

@router.get("/")
async def list_items(): ...
```

## include_router 注册时机

在 app 对象创建后、startup 前调用 `include_router`，不要在模块级延迟加载：

```python
app.include_router(items.router)
app.include_router(users.router, prefix="/users")
```

## 路由命名

- endpoint function 使用描述性名称，如 `read_items`、`update_user`
- 路径参数使用下划线：`/items/{item_id}`
- 避免深层嵌套路由（不超过 3 层）

来源：分析 `fastapi/routing.py` 的 `APIRouter` 注册机制和 `applications.py:FastAPI.include_router`。

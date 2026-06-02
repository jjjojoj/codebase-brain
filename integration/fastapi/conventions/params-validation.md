---
module: params
title: FastAPI 参数与校验约定
tags: [params, validation, pydantic, annotated]
---

# 参数与校验约定

## Annotated + Doc 模式

FastAPI 自身使用 `Annotated[type, Doc("description")]` 声明参数文档。用户代码应使用：

```python
from typing import Annotated
from pydantic import BaseModel

class ItemCreate(BaseModel):
    name: str
    price: float
    is_offer: bool | None = None

@app.post("/items/")
async def create_item(item: Annotated[ItemCreate, Body()]):
    return item
```

## Query/Path/Body 参数区分

- `Query()`：URL 查询参数，可选/必填
- `Path()`：路径参数，总是必填
- `Body()`：请求体，使用 Pydantic model
- `Depends()`：依赖注入，不直接对应 HTTP 参数

## Pydantic 模型验证

请求体验证失败时 FastAPI 自动返回 422，包含结构化错误信息：

```json
{"detail": [{"type": "missing", "loc": ["query", "q"], "msg": "Field required"}]}
```

来源：`params.py`、`param_functions.py` 和 `dependencies/utils.py:get_body_field`。

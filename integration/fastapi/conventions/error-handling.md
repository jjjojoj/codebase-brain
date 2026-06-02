---
module: errors
title: FastAPI 错误处理约定
tags: [errors, exceptions, http, validation]
---

# 错误处理约定

## HTTPException 使用

客户端错误用 `HTTPException`，不要用于服务端内部错误：

```python
from fastapi import HTTPException

@app.get("/items/{item_id}")
async def read_item(item_id: str):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"item": items[item_id]}
```

## 异常继承层次

FastAPI 的异常体系从宽到窄：

- `FastAPIError(RuntimeError)`：通用框架错误
- `ValidationException(Exception)`：请求/响应验证失败
  - `RequestValidationError`：请求体/参数不符合 Schema → 返回 422
  - `ResponseValidationError`：响应不符合 response_model → 内部错误
- `DependencyScopeError`：依赖作用域冲突

## 自定义异常处理器

继承 `exception_handlers.py` 的 handler 模式：

```python
async def http_exception_handler(request, exc):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
```

来源：`exceptions.py` 异常继承链和 `exception_handlers.py` 的 handler 函数。

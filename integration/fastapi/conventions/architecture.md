---
module: architecture
title: FastAPI 应用架构约定
tags: [architecture, middleware, starlette, asgi]
---

# 应用架构约定

## FastAPI 继承 Starlette

`FastAPI(app)` 继承 `starlette.applications.Starlette`，叠加 OpenAPI 生成、依赖注入、参数校验。核心中间件链（由 Starlette 管理）：

```
ServerErrorMiddleware → ExceptionMiddleware → user middleware → FastAPI router
```

## 中间件注册顺序

自定义中间件按注册顺序执行（LIFO）：

```python
app.add_middleware(AuthMiddleware)       # 最后执行
app.add_middleware(LoggingMiddleware)    # 先执行
```

## 文件组织

大型 FastAPI 项目推荐结构：

```
app/
  api/routes/    → 路由模块
  core/          → 配置、安全、依赖
  models/        → Pydantic schema
  services/      → 业务逻辑
```

来源：`applications.py:FastAPI.__init__`、`middleware/` 和 Starlette 中间件栈。

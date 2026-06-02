---
module: dependencies
title: FastAPI 依赖注入约定
tags: [di, depends, dependency-injection, testing]
---

# 依赖注入约定

## Depends() 函数设计

依赖函数应是 async 协程或普通同步函数，使用 Python 类型提示声明返回值：

```python
async def common_parameters(q: str, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

@router.get("/items/")
async def list_items(commons: dict = Depends(common_parameters)):
    return commons
```

## dependency_override 测试模式

测试中使用 `app.dependency_overrides` 替换真实依赖，测试后必须清空：

```python
app.dependency_overrides[common_parameters] = overrider_dependency
response = client.get("/items/")
assert response.status_code == 200
app.dependency_overrides = {}  # 必须清理，避免污染其他测试
```

## 依赖作用域

- `Depends()` 默认作用域为请求级（request scope）
- 内部依赖不应声明比外部依赖更窄的作用域（否则触发 `DependencyScopeError`）

来源：`dependencies/utils.py` 的 `solve_dependencies` 和 `test_dependency_overrides.py`。

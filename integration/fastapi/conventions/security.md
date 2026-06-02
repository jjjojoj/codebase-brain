---
module: security
title: FastAPI 安全认证约定
tags: [security, oauth2, authentication, authorization]
---

# 安全认证约定

## OAuth2 方案定义

使用 `OAuth2AuthorizationCodeBearer` 等方案类声明认证方式：

```python
from fastapi.security import OAuth2AuthorizationCodeBearer

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="authorize",
    tokenUrl="token",
    auto_error=True
)
```

## Security() 依赖注入

使用 `Security()` 替代 `Depends()` 声明安全依赖，以在 OpenAPI schema 中添加 security 信息：

```python
@app.get("/items/")
async def read_items(token: str | None = Security(oauth2_scheme)):
    return {"token": token}
```

## 认证失败处理

`auto_error=True` 时，缺失/无效 token 自动返回 401 `{"detail": "Not authenticated"}`。

GitHub OAuth2 scopes 使用 `SecurityScopes` 声明权限范围。

来源：`security/oauth2.py`、`security/base.py` 和 `test_security_oauth2_authorization_code_bearer.py`。

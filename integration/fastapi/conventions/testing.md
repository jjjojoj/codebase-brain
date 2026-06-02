---
module: testing
title: FastAPI 测试编写约定
tags: [testing, testclient, pytest, parametrize]
---

# 测试编写约定

## TestClient 模式

使用 `fastapi.testclient.TestClient`，在模块级创建 app 和 client 实例：

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()
client = TestClient(app)

def test_read_items():
    response = client.get("/items/")
    assert response.status_code == 200
```

## pytest.parametrize 替代重复测试

相同逻辑不同输入的测试用例，用 `@pytest.mark.parametrize` 消除重复：

```python
@pytest.mark.parametrize("url,status_code,expected", [
    ("/main-depends/", 200, {"in": "main-depends", "params": {...}}),
    ("/main-depends/?q=foo", 200, {"in": "main-depends", "params": {...}}),
])
def test_override_simple(url, status_code, expected):
    response = client.get(url)
    assert response.status_code == status_code
    assert response.json() == expected
```

## 测试覆盖要求

每个 endpoint 必须覆盖以下场景：
1. 缺少必要参数 → 422
2. 有效参数 → 200
3. OpenAPI schema 一致性检查

来源：`tests/test_dependency_overrides.py` 和 `tests/test_security_*.py`。

# pre-commit 钩子指南

**中文** | [English](pre-commit.en.md)

本项目使用 [pre-commit](https://pre-commit.com) 在每次 `git commit` 前自动运行检查，
保障代码质量并避免误提交敏感信息。

## 安装
```bash
pip install pre-commit          # 或 pip install -r requirements-dev.txt
pre-commit install              # 在 .git/hooks 安装钩子
```

## 包含的检查
配置文件：[`.pre-commit-config.yaml`](../.pre-commit-config.yaml)

| 钩子 | 作用 |
|------|------|
| `trailing-whitespace` | 移除行尾多余空格 |
| `end-of-file-fixer` | 确保文件以单个换行结尾 |
| `check-yaml` | 校验 YAML 语法 |
| `check-json` | 校验 JSON 语法 |
| `check-added-large-files` | 阻止提交超过 1MB 的大文件 |
| `detect-private-key` | 检测误提交的私钥 |
| `check-merge-conflict` | 检测残留的合并冲突标记 |
| `pytest-unit`（本地） | 运行 `pytest -q` 单元测试（48 项，Mock 模式） |

## 使用
- 安装后，`git commit` 会自动触发上述检查；**任一失败将阻止提交**。
- 部分钩子（如去尾空格）会自动修复文件，此时需重新 `git add` 后再次提交。

## 常用命令
```bash
pre-commit run --all-files      # 手动对全部文件运行一次
pre-commit run pytest-unit      # 只运行单元测试钩子
pre-commit autoupdate           # 升级各钩子版本
SKIP=pytest-unit git commit ... # 临时跳过某个钩子（不推荐）
git commit --no-verify ...      # 跳过全部钩子（仅紧急情况）
```

## 说明
- `pytest-unit` 使用 `language: system`，依赖本地已安装的 Python 与 pytest
  （`pip install -r requirements-dev.txt`）。
- **提交前请先激活虚拟环境**（`.\.venv\Scripts\Activate.ps1` 或 `source .venv/bin/activate`），
  以确保 `python -m pytest` 使用的是装好依赖的解释器。
- 单元测试通过 `tests/conftest.py` 将数据路径重定向到临时目录，不污染本地数据。

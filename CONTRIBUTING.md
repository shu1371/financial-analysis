# 贡献指南

感谢你愿意为这个项目贡献代码。

## 本地开发

```bash
git clone https://github.com/shu1371/financial-analysis.git
cd financial-analysis
pip install -r requirements.txt
cp config.example.py config.py   # 填写 MySQL 配置（可选）
streamlit run app.py
```

浏览器访问 http://localhost:8501。

## 测试

```bash
python -m compileall -q app.py database pages utils
```

提交前请确保语法检查通过。

## 提交规范

提交信息遵循 Conventional Commits：

- `feat:` 新功能
- `fix:` 缺陷修复
- `docs:` 文档
- `test:` 测试
- `chore:` 杂项

## Pull Request

1. 从 `master` 新建分支。
2. 提交清晰的、单一职责的改动。
3. 运行并通过语法检查。
4. 提交 PR 并描述改动内容。
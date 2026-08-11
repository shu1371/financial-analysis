# 安全说明

## 报告安全问题

如果发现本项目的安全漏洞，请优先使用 GitHub 的私有漏洞报告（Private vulnerability reporting）功能提交，避免公开披露细节。

也可以通过邮件联系维护者：lxtoxyf@163.com。

## 安全相关文档

本仓库的 [XSS_REPORT.md](XSS_REPORT.md) 记录了安全测试发现与修复过程，欢迎查阅。

## 注意事项

- `config.py` 与 `.env` 已在 `.gitignore` 中，禁止提交数据库密码等敏感信息。
- 用户密码在代码中以哈希形式存储，请勿明文保存。
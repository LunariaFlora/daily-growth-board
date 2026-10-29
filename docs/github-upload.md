# 上传 GitHub

使用另行准备的 `github-ready/daily-growth-board` 干净目录，而不是开发工作目录的旧 Git 历史。

1. 项目已采用 MIT 许可证，上传时一并保留 LICENSE 和第三方许可。
2. 在 GitHub 新建空仓库，推荐名称 `daily-growth-board`，不要自动创建 README。
3. 在干净目录打开终端，按 GitHub 提供的仓库地址执行：

```powershell
git remote add origin <你的仓库地址>
git push -u origin main
```

也可解压 `日有所积-GitHub源码.zip` 后通过 GitHub 网页上传里面的文件。不要上传自己的 data、运行环境、浏览器配置或开发目录的 .git。

推送后查看 Actions 测试。准备发布时创建 `v1.0.0` Release，粘贴 docs/release-notes.md 内容，上传便携 ZIP 与 SHA-256 文件。当前尚未创建远程仓库、推送或发布 Release。

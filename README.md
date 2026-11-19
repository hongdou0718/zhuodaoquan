# 纸间：个人文章网站

这是一个可以直接发布到公网的个人写作网站。文章使用 Markdown 编写，构建后是纯静态网页，不需要数据库、服务器或第三方 Python 包。

## 本地预览

在 `personal-blog` 目录中运行：

```powershell
python build.py
python -m http.server 4173 --directory dist
```

然后打开 `http://localhost:4173`。

## 修改网站信息

打开 `site.json`，修改以下字段：

- `title`：网站名称
- `tagline`：首页短句
- `description`：网站简介
- `author`：作者名称
- `email`：联系邮箱
- `home_note`：首页“写在前面”
- `about_summary`：首页关于区域的简介
- `base_url`：上线后的完整网址，例如 `https://your-name.github.io/my-writing`

同时修改 `content/about.md` 中的个人介绍和邮箱。

## 发表新文章

在 `content/posts/` 中新建一个 Markdown 文件，例如：

```text
content/posts/2026-11-20-my-new-post.md
```

文章开头加入：

```markdown
---
title: 文章标题
date: 2026-11-20
summary: 显示在首页的一句话摘要。
tag: 随笔
---

正文从这里开始。
```

保存后重新运行 `python build.py`。文章会自动出现在首页、RSS 和站点地图中。

如果暂时不想公开，可以加入：

```markdown
draft: true
```

> 重要：文章源文件只放在 `content/posts/`，不要直接修改 `dist/posts/`。`dist` 是自动生成的结果，下次构建时会被替换。

构建脚本会先在临时目录中生成完整网站，只有全部页面都成功生成后才会替换旧版本。因此即使某次文章格式有误，也不会再出现首页还在、文章页却全部消失的情况。

## 免费发布到 GitHub Pages

1. 注册并登录 [GitHub](https://github.com)。
2. 新建一个仓库，例如 `my-writing`，设为公开。
3. 把 `personal-blog` 目录中的全部文件上传到仓库。
4. 打开仓库的 `Settings → Pages`。
5. 在 `Build and deployment` 中将 `Source` 设为 `GitHub Actions`。
6. 回到仓库的 `Actions` 页面，等待 `Deploy writing site` 完成。
7. 在 `Settings → Pages` 查看公开网址。

以后再修改文章，只要把新文件提交到 `main` 分支，网站就会自动更新。

GitHub Pages 的免费网址通常是：

```text
https://你的用户名.github.io/仓库名/
```

上线后把该网址填写到 `site.json` 的 `base_url`。

## GitHub Pages 打开很慢怎么办

GitHub Pages 在部分网络环境中可能非常慢，甚至无法稳定打开。这个网站的构建结果只有约 0.2 MB，因此通常不是网站本身太大，而是托管平台的网络问题。

最快的替代方案是 Netlify：

### 临时快速发布

1. 打开 [Netlify Drop](https://app.netlify.com/drop)。
2. 登录 Netlify。
3. 把 `personal-blog/dist` 文件夹拖进页面。
4. Netlify 会立即生成一个公开网址。

以后修改文章时，先运行 `python build.py`，再重新拖入新的 `dist` 文件夹即可。

### 长期自动发布

1. 登录 Netlify，选择 `Add new site → Import an existing project`。
2. 连接存放网站的 GitHub 仓库。
3. Netlify 会自动读取项目中的 `netlify.toml`。
4. 构建命令使用 `python build.py`，发布目录使用 `dist`。
5. 以后每次推送文章到 GitHub，Netlify 都会自动更新公开网站。

Netlify 生成的站点不依赖 GitHub Pages 的 `github.io` 域名，通常更适合分享给其他人。

## 使用自己的域名

在 GitHub 仓库的 `Settings → Pages → Custom domain` 中填写域名，并按页面提示配置 DNS。域名本身通常需要单独购买。

## 公开范围

部署到 GitHub Pages 后，任何拿到网址的人都可以阅读。若以后希望增加评论、邮件订阅或私密文章，可以在此基础上继续接入相应服务。

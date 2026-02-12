# 个人博客？

> 用于试手的个人博客，顺便记录操作流程。本篇并未遵守中文写作规范

## 概述

**GitHub Pages**是一项静态站点托管服务，它直接从GitHub上的存储库获取HTML、CSS和JavaScript文件来发布网站。其并非用于提供免费的商用Web托管服务，并有如下限制：

1. 每个GitHub账户只能有一个GitHub Pages用户站点
2. GitHub Pages站点网站体积（最终生成的静态文件）限制为1GB
3. GitHub Pages站点部署（构建/生成）时间限制为10分钟（除非使用GitHub Actions自行构建并推送静态文件）
4. GitHub Pages站点的每小时生成限制为10次（不能频繁推送代码进行网页生成，除非使用GitHub Actions自行构建并推送静态文件）
5. GitHub Pages站点的带宽限制为每月100GB（每月访问数据总量限制）
6. 为保障GitHub Pages服务良好运行，站点可能会被限制速率（如遭受DDoS攻击）

**静态网站**是由预先写好的HTML、CSS和JavaScript文件组成的网站，这些文件在服务器上是静态的，无论如何访问，服务器都返回同样的文件。相较于动态网站，其不需要后端逻辑，发布后无法更改内容。常见的静态网站生成器有`Jekyll`、`Hugo`、`Hexo`、`Next.js`等

GitHub推荐初学者使用**Jekyll**构建简单的网站，Jekyll内置GitHub Pages支持和简化的静态网站构建过程，允许用户直接使用Markdown或HTML文件生成网站

## 流程（探索中）

### GitHub引导流程

> 下面的所有步骤均可参考GitHub给出的引导，使用该流程需要少量markdown和github经验

1. 直接访问<https://github.com/skills/github-pages/>，点击Readme中的`Start course`按钮
2. 修改仓库名（建议使用`<yourname>.github.io`），点击`Create repository`创建仓库
3. 创建仓库后，等待一段时间，刷新页面（GitHub的bot会为你初始化仓库）
4. 切换到`my-pages`分支，打开`_config.yml`文件，参考下面的第一段代码修改，随后提交，刷新页面（等待仓库更新）
5. 打开`index.md`以`markdown`格式编写简单的首页，随后提交，刷新页面（等待仓库更新）
6. 添加文件，命名为`_posts/YYYY-MM-DD-title.md`，标题中严格填写当前日期和标题
7. 参考下面的第二段代码修改刚创建的文件，随后提交，刷新页面（等待仓库更新）
8. 将`my-pages`分支下的修改合并到`main`，随后即可访问`https://<youename>.github.io/`查看刚创建的站点效果
9. 你可以在`my-pages`分支下`.github/steps/`下查看所有步骤

```yml
theme: minima       # 此处可选择其它主题
title: <yourtitle>  # 修改为合适的标题
author: <yourname>  # 修改为你的名字
description: <yourdescription>  # 添加你的描述
```

```yml
---
title: "YOUR-TITLE" # 修改此处的`YOUR-TITLE`，其中空格应以`-`替代
date: YYYY-MM-DD    # 修改此处的`YYYY-MM-DD`为当前日期
categories: [博客, 教程]    # 博客分类
tags: [github, jekyll]      # 博客标签
---

<!-- 下面是正文内容，支持Markdown语法 -->
```

### 简单流程（无效）

> 静态网站文件的生成不在本流程中，GitHub Pages默认使用Jekyll生成站点，可以在发布源的根目录中创建一个名为`.nojekyll`的空文件来禁用Jekyll生成过程

1. 生成自己的静态网站文件，放在根目录或`main/docs/`下，GitHub会自动识别并发布网站（确保在仓库设置的`GitHub Pages`标签中选择相应的分支）

## Jekyll

一个Jekyll网站项目结构如下，Jekyll支持使用html或markdown作为内容载体：

```shell
main/
├── _data/             # 数据文件目录
├── _drafts/           # 草稿目录
├── _includes/         # 可复用的代码片段
├── _layouts/          # 页面布局模板
├── _posts/            # 博客文章目录
│   ├── YYYY-MM-DD-title.xx # 博客文章（格式严格限制）
│   └── ...
├── _sass/             # Sass/SCSS样式文件
├── _site/             # 生成的静态网站（输出目录）
├── assets/            # 静态资源（图片、CSS、JS）
├── _config.yml        # 核心配置文件
├── .jekyll-metadata   # 内部元数据缓存
├── index.html         # 网站首页入口
└── Gemfile            # Ruby 依赖管理
```

## 参考

1. [GitHub文档：GitHub Pages](https://docs.github.com/zh/pages/getting-started-with-github-pages/what-is-github-pages)
2. [GitHub Skills：github-pages](https://github.com/skills/github-pages/)
3. [Jekyll中文](https://jekyllcn.com/docs/home/)

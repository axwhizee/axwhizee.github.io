# 个人博客？

> 用于试手的个人博客，顺便记录操作流程。本篇并未遵守中文写作规范

## 概述

**GitHub Pages**是一项静态站点托管服务，它直接从 GitHub 上的存储库获取HTML、CSS和JavaScript文件来发布网站。其并非用于提供免费的商用Web托管服务，并有如下限制：

1. 每个GitHub账户只能有一个GitHub Pages用户站点
2. GitHub Pages站点网站体积（最终生成的静态文件）限制为1GB
3. GitHub Pages站点部署（构建/生成）时间限制为10分钟（除非使用GitHub Actions自行构建并推送静态文件）
4. GitHub Pages站点的每小时生成限制为10次（不能频繁推送代码进行网页生成，除非使用GitHub Actions自行构建并推送静态文件）
5. GitHub Pages站点的带宽限制为每月100GB（每月访问数据总量限制）
6. 为保障GitHub Pages服务良好运行，站点可能会被限制速率（如遭受DDoS攻击）

GitHub推荐初学者使用**Jekyll**构建简单的网站，Jekyll是一个静态站点生成器，内置GitHub Pages支持和简化的构建过程，允许用户直接使用Markdown或HTML文件生成网站

## 流程（探索）

### GitHub引导流程

> 下面的所有步骤均可参考GitHub给出的引导，使用该流程需要少量markdown和github经验

1. 直接访问<https://github.com/skills/github-pages/>，点击Readme中的`Start course`按钮
2. 修改仓库名（建议使用`<yourname>.github.io`），点击`Create repository`创建仓库
3. 创建仓库后，等待一段时间，刷新页面（GitHub的bot会为你初始化仓库）
4. 切换到`my-pages`分支，打开`_config.yml`文件，参考第一段代码修改，随后提交
5. 检查pull request，合并`github-actions[bot]`提交的请求，刷新页面
6. 打开`index.md`以`markdown`格式编写简单的首页，随后提交，同步骤`5`
7. 添加文件，命名为`_posts/YYYY-MM-DD-title.md`，标题中严格填写当前日期
8. 参考第二段代码修改刚创建的文件，随后提交，同步骤`5`
9. 将`my-pages`分支下的修改合并到`main`
10. 浏览器访问`https://axwhizee.github.io/`查看刚创建的站点效果
11. 你可以在`my-pages`分支下`.github/steps/`下查看所有步骤

```yml
theme: minima
title: <yourtitle>  # 修改为合适的标题
author: <yourname>  # 修改为你的名字
description: <yourdescription>  # 添加你的描述
```

```yml
---
title: "YOUR-TITLE" # 修改此处的`YOUR-TITLE`，其中空格应用`-`替代
date: YYYY-MM-DD    # 修改此处的`YYYY-MM-DD`为当前日期
categories: [博客, 教程]    # 博客分类
tags: [github, jekyll]      # 博客标签
---

<!-- 下面是正文内容，支持Markdown语法 -->
```
### 简单流程

1. 创建

## 项目结构

一个Jekyll网站项目结构如下：

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
├── index.html         # 首页入口，markdown文件亦可
└── Gemfile            # Ruby 依赖管理
```

## 参考

1. [GitHub文档：GitHub Pages](https://docs.github.com/zh/pages/getting-started-with-github-pages/what-is-github-pages)
2. [GitHub Skills：github-pages](https://github.com/skills/github-pages/)
3. [Jekyll中文](https://jekyllcn.com/docs/home/)

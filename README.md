# 个人博客？

> 用于试手的个人博客，顺便记录操作流程。本篇并未遵守中文写作规范

关于 **Github Pages** 的笔记在 Coding 仓库（还没准备好开放）中，下面是一个 Jekyll 网站项目的结构：（当然，我没有搭建 Jekyll 环境自己构建网页，依赖的是 **Github Actions** 的自动构建）

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

在AI的辅助下，为博客添加了一个每周更新文章的 Python 脚本，通过 Github Actions 自动推送，并且通知指定邮箱

## 参考

1. [GitHub Actions : Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)

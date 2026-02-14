# 个人博客？

> 用于试手的个人博客，顺便记录操作流程。本篇并未遵守中文写作规范

关于**Github Pages**的笔记在Coding仓库（还没准备好开放）中，下面是一个Jekyll网站项目的结构：

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

当然，我没有搭建Jekyll环境自己构建网页，依赖的是**Github Actions**的自动构建

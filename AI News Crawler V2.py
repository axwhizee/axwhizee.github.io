import os
import datetime
import requests
from openai import OpenAI

# ===== 配置区 =====
DASHSCOPE_API_KEY = "sk-你的API密钥"  # ← 替换为你自己的Key
BLOG_TITLE = "AI前沿速递"
AUTHOR = "你的名字"

# 新闻源（可扩展）
NEWS_SOURCES = [
    "https://arxiv.org/list/cs.AI/recent",
    "https://deepmind.google/blog/",
    "https://openai.com/blog",
    # 可添加更多
]

# ===== 工具函数 =====
def fetch_news_snippets():
    """模拟抓取新闻标题和摘要（实际可替换为真实爬虫）"""
    # TODO: 这里可集成 BeautifulSoup 或调用 RSS/ArXiv API
    return [
        "Google DeepMind 发布新一代推理模型 Gemini 2.5",
        "OpenAI 推出 o1-mini，专注代码生成与数学推理",
        "Meta 开源 Llama 4-Mini，支持 128K 上下文",
        "中国团队在 NeurIPS 2025 提出新型视觉-语言对齐方法"
    ]

def generate_summary_with_bailian(news_list):
    """调用阿里百炼生成总结文章"""
    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    
    prompt = f"""你是一位科技专栏作家。请根据以下今日AI领域动态，撰写一篇800字左右的中文博客文章：
- 标题要吸引人
- 分段清晰（引言、主体、展望）
- 语言专业但易懂
- 结尾鼓励读者思考

今日动态：
{chr(10).join(f'- {item}' for item in news_list)}

请直接输出文章内容，不要包含任何说明文字。"""

    try:
        response = client.chat.completions.create(
            model="qwen-plus",  # 平衡效果与成本
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"调用百炼失败: {e}")
        return "今日AI动态总结生成失败，请检查网络或API配额。"

def render_html(title, date_str, content):
    """渲染单篇文章HTML"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title} - {BLOG_TITLE}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header><h1>{BLOG_TITLE}</h1></header>
    <main>
        <article>
            <h2>{title}</h2>
            <p class="meta">发布于 {date_str} | 作者 {AUTHOR}</p>
            <div class="content">
                {content.replace(chr(10), '<br>')}
            </div>
        </article>
    </main>
    <footer><a href="/">← 返回首页</a></footer>
</body>
</html>"""

def build_index(posts_info):
    """生成首页"""
    items_html = ""
    for post in sorted(posts_info, key=lambda x: x['date'], reverse=True):
        items_html += f'<li><a href="{post["url"]}">{post["title"]}</a> ({post["date"]})</li>'
    
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{BLOG_TITLE}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header><h1>{BLOG_TITLE}</h1></header>
    <main>
        <h2>最新文章</h2>
        <ul>{items_html}</ul>
    </main>
    <footer>Powered by Python + 阿里百炼</footer>
</body>
</html>"""

# ===== 主流程 =====
def main():
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")
    filename = f"{date_str}-ai-daily.html"
    
    print("🔍 正在抓取AI新闻...")
    news = fetch_news_snippets()
    
    print("🧠 正在调用阿里百炼生成总结...")
    summary = generate_summary_with_bailian(news)
    
    print("📝 正在生成文章页面...")
    title = f"AI前沿速递 | {date_str}"
    html_content = render_html(title, date_str, summary)
    
    # 创建目录
    os.makedirs("posts", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    
    # 保存文章
    with open(f"posts/{filename}", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # 生成首页
    posts_info = []
    for f in os.listdir("posts"):
        if f.endswith(".html"):
            date_part = f.split("-ai-daily")
            posts_info.append({
                "title": f"AI前沿速递 | {date_part}",
                "date": date_part,
                "url": f"/posts/{f}"
            })
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(build_index(posts_info))
    
    # 创建简单CSS（首次运行时）
    if not os.path.exists("static/style.css"):
        with open("static/style.css", "w") as f:
            f.write("""
body { font-family: 'Segoe UI', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }
header h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
.meta { color: #7f8c8d; font-style: italic; }
.content { margin: 20px 0; }
footer { margin-top: 40px; text-align: center; color: #95a5a6; }
""")
    
    print(f"✅ 今日博客已生成！\n   文章路径: posts/{filename}\n   请提交到 GitHub 并访问你的 Pages 站点。")

if __name__ == "__main__":
    main()

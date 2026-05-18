"""
AI 领域周报生成器

功能概述：
1. 从多个顶级 AI 机构的 RSS 源抓取最近 7 天内的文章；
2. 提取每篇文章的标题、链接、摘要和来源；
3. 将汇总信息通过阿里云百炼（DashScope）平台的大模型生成一份结构化的 Markdown 周报；
4. 将最终报告生成为新的博客文章。

依赖库说明：
- feedparser：解析 RSS/Atom 订阅源
- requests：发起 HTTP 请求获取 RSS 内容
- openai：使用 OpenAI 兼容接口调用 DashScope 的大模型
- datetime / email.utils：处理不同格式的发布时间
"""

import os
import requests
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_tz, mktime_tz  # 用于解析 RFC 2822 格式的日期（常见于 RSS）
import feedparser
from chatbot_oai import BotConfig, ChatBot


def parse_rss_date(date_str):
    """尝试将 RSS 中的日期字符串解析为标准的 datetime 对象（无时区信息，但按 UTC 处理）。
    
    RSS 中的日期格式不统一，可能为：
    - RFC 2822 格式（如 "Mon, 01 Jan 2024 12:00:00 GMT"）
    - ISO 8601 格式（如 "2024-01-01T12:00:00Z" 或带时区偏移）
    
    参数:
        date_str (str): 原始日期字符串（可能来自 entry.published 或 entry.updated）
    
    返回:
        datetime | None: 成功解析则返回 naive datetime（视为 UTC），否则返回 None
    """
    if not date_str:
        return None

    # 首先尝试使用 email.utils 解析 RFC 2822 格式（最常见于 RSS）
    try:
        parsed_tuple = parsedate_tz(date_str)
        if parsed_tuple:
            timestamp = mktime_tz(parsed_tuple)  # 转为 Unix 时间戳（考虑时区）
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return dt.replace(tzinfo=None)  # 返回无时区对象，但内容是 UTC 时间
    except Exception:
        pass  # 若失败，继续尝试其他格式

    # 若上述失败，尝试几种常见的 ISO 格式
    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S%z"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            # 如果解析结果没有时区信息，则默认为 UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # 转换为 UTC 并去除时区信息（保持与上一分支一致）
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            continue  # 格式不匹配，尝试下一个

    # 所有尝试均失败
    return None

def fetch_rss_feed_entries(rss_source):
    """从指定的RSS源抓取文章条目列表"""
    articles = []
    for url in rss_source:
        try:
            print(f"Fetching: {url}")
            # 发起 GET 请求获取 RSS 内容，设置超时防止卡死
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()  # 若状态码非 2xx 则抛出异常
            # 使用 feedparser 解析 RSS 内容
            feed = feedparser.parse(resp.content)
            # 遍历每篇文章（entry）
            for entry in feed.entries:
                # 优先使用 'published'，若无则尝试 'updated'
                date_str = getattr(entry, 'published', None) or getattr(entry, 'updated', None)
                pub_date = parse_rss_date(date_str) if date_str else None
                # 仅保留过去 7 天内的文章（注意：SEVEN_DAYS_AGO 是带时区的，需对齐）
                if pub_date and pub_date >= SEVEN_DAYS_AGO.replace(tzinfo=None):
                    title = getattr(entry, 'title', 'No Title').strip()
                    link = getattr(entry, 'link', '').strip()
                    # 获取摘要并做简单清洗：去换行、截断
                    summary = getattr(entry, 'summary', '').strip().replace('\n', ' ')[:800]
                    source = getattr(feed.feed, 'title', 'Unknown Source').strip()
                    articles.append({
                        'title': title,
                        'link': link,
                        'summary': summary,
                        'source': source,
                        'published': pub_date.isoformat()  # 转为 ISO 字符串便于排序和输出
                    })
                    
        except Exception as e:
            # 捕获任意异常（网络错误、解析失败等），记录日志但不中断整体流程
            print(f"⚠️ Error fetching {url}: {e}")
            continue

    # 按发布时间倒序排列（最新在前）
    articles.sort(key=lambda x: x['published'], reverse=True)
    return articles

def out_put(content: str, file_path: str = "./output.md")->None:
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        raise FileNotFoundError(f"导出文件{file_path}失败：{e}\n")
    else:
        print(f"文件{file_path}生成成功！\n")

if __name__ == "__main__":
    # 定义要监控的 AI 领域权威博客 RSS 地址列表
    RSS_SOURCE = [
        "https://research.google/blog/rss/",        # Google AI Blog
        "https://openai.com/news/rss.xml",          # OpenAI Blog
        "https://deepmind.com/blog/feed/",          # DeepMind Blog
        "https://huggingface.co/blog/feed.xml",     # Hugging Face Blog
        "https://bair.berkeley.edu/blog/feed.xml"   # BAIR (Berkeley AI Research)
    ]
    MODULE = "qwen3.6-plus"
    # 计算“7天前”的 UTC 时间点，用于过滤近期文章
    SEVEN_DAYS_AGO = datetime.now(timezone.utc) - timedelta(days=7)

    print("正在抓取最近7天的AI前沿文章...")
    articles = fetch_rss_feed_entries(RSS_SOURCE)
    if not articles:
        raise ValueError("# AI领域最新进展周报\n\n本周无新发布内容。")
    print(f"✅ 共获取 {len(articles)} 篇新文章。\n")

    print(f"正在调用 {MODULE}（通过 OpenAI 兼容接口）生成周报...")
    # 构建提供给大模型的原始上下文
    content = "以下是过去一周来自 Google AI、OpenAI、DeepMind、Hugging Face 和 BAIR 等顶级 AI 机构的最新文章摘要：\n\n"
    for art in articles:
        content += f"- **{art['title']}** （来源：{art['source']}）\n"
        if art['summary']:
            content += f"  摘要：{art['summary']}\n"
        content += f"  链接：{art['link']}\n\n"
    # 构造提示词（Prompt），明确要求模型输出结构化、有洞察力的分析
    prompt = ("请基于以下近期 AI 领域的技术博客摘要（含链接），撰写一份名为《AI领域最新进展周报》的报告，要求：\n\n"
        "1. 报告必须使用 Markdown 格式"
        "2. 标题为：**AI领域最新进展周报**（带时间）"
        "3. 内容需包含："
        "   - 当前主要发展方向（如多模态、推理能力、开源生态、具身智能等）"
        "   - 列举本周突出的流行产品或技术（如新模型、框架、工具），附相关链接"
        f"<contents>\n{content}\n</contents>"
        )

    config = BotConfig(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model=MODULE,
        env_key_name="DASHSCOPE_API_KEY",
        temperature=1,  # 无语
        extra_body={"enable_thinking": False},  # 适用于 DashScope 平台的参数，关闭思考功能
    )
    result = ChatBot(config).chat(prompt)
    # 获取日期以便生成文档
    date = datetime.now().date()
    # 将报告写入文件，头部添加 Front Matter（适用于静态博客如 Hugo）
    out_put(f"""---\ntitle: "AI Weekly Report({date})"\ndate: {date}\n---\n{result}""",
            f"./_posts/{date}-Post.md")
    print(f"📄 周报生成成功！\n使用Token：{ChatBot.token_usage}")

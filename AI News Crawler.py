#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI News Crawler - 自动化AI领域新闻聚合与摘要生成工具

功能概述：
- 从多个AI权威数据源获取最新新闻和论文
- 调用阿里百炼API进行智能摘要生成
- 生成符合Jekyll标准的Markdown格式文章
- 自动保存到_posts目录供Jekyll博客使用
- 支持代理配置、请求限流、自动重试等高级功能

支持的数据源：
- ArXiv AI相关分类：cs.AI, cs.LG, cs.CL, cs.CV
- Google DeepMind Blog
- OpenAI Blog
- TechCrunch AI/ML
- MIT Technology Review
- Wired AI报道
- The Verge AI新闻
- 机器之心（中文AI资讯）

安装依赖：
pip install requests feedparser beautifulsoup4 pyyaml

配置文件示例 (config.yaml)：
# config.yaml
ali_baillan:
  api_key: "YOUR_ALI_BAILLAN_API_KEY"
  endpoint: "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
  
rss_sources:
  - url: "https://rss.arxiv.org/rss/cs.AI"
    name: "ArXiv AI"
    type: "academic"
  - url: "https://deepmind.google/blog/rss.xml"
    name: "Google DeepMind"
    type: "blog"
  - url: "https://openai.com/blog/rss.xml"
    name: "OpenAI"
    type: "blog"
  
crawler:
  max_articles: 20
  days_back: 7
  output_dir: "./_posts"
  log_level: "INFO"

使用方式：
python ai_news_crawler.py --config config.yaml
"""

import requests
import feedparser
from bs4 import BeautifulSoup
import yaml
import os
import json
import hashlib
import logging
import re
from datetime import datetime, timedelta
import time
import argparse
import sys
import signal
import html
import random
from typing import List, Dict, Optional, Any


# ==========================================
# 1. 日志管理器
# ==========================================
class LoggerManager:
    """高级日志管理器，支持日志轮转和格式化"""

    @staticmethod
    def setup_logging(log_level="INFO", log_file="crawler.log"):
        """
        配置日志系统
        
        Args:
            log_level (str): 日志级别
            log_file (str): 日志文件路径
        """
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            numeric_level = logging.INFO
        
        # 定义日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # 文件记录更详细的日志
        
        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        
        # 设置第三方库的日志级别，避免过于嘈杂
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)


# ==========================================
# 2. 文本规范化工具
# ==========================================
class TextNormalizer:
    """文本处理工具类，用于清理和规范化文本"""

    @staticmethod
    def clean_html(raw_html):
        """
        移除HTML标签并清理文本
        
        Args:
            raw_html (str): 原始HTML字符串
            
        Returns:
            str: 清理后的纯文本
        """
        if not raw_html:
            return ""
        
        # 解码HTML实体（如 & -> &）
        decoded_html = html.unescape(raw_html)
        
        # 使用BeautifulSoup移除标签
        soup = BeautifulSoup(decoded_html, 'html.parser')
        
        # 移除不需要的标签
        for script in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            script.decompose()
        
        # 获取文本
        text = soup.get_text(separator=' ')
        
        # 清理多余的空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    @staticmethod
    def normalize_whitespace(text):
        """规范化空白字符"""
        return re.sub(r'[ \t\r\n]+', ' ', text).strip()

    @staticmethod
    def truncate_text(text, max_length=5000, suffix="..."):
        """截断过长的文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(' ', 1)[0] + suffix


# ==========================================
# 3. 限流器
# ==========================================
class RateLimiter:
    """简单的请求限流器，防止请求过于频繁"""

    def __init__(self, min_interval=1.0):
        """
        初始化限流器
        
        Args:
            min_interval (float): 两次请求之间的最小间隔（秒）
        """
        self.min_interval = min_interval
        self.last_called = 0

    def wait(self):
        """等待直到满足最小间隔"""
        current_time = time.time()
        elapsed = current_time - self.last_called
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        self.last_called = time.time()


# ==========================================
# 4. 配置管理器
# ==========================================
class ConfigManager:
    """配置管理类，负责读取、验证和提供配置"""

    def __init__(self, config_path):
        """
        初始化配置管理器
        
        Args:
            config_path (str): 配置文件路径
        """
        self.config_path = config_path
        self.config = {}
        self.load_config()
        self.validate_config()
        self._set_defaults()
    
    def load_config(self):
        """从YAML文件加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            logging.info(f"成功加载配置文件: {self.config_path}")
        except FileNotFoundError:
            logging.error(f"配置文件未找到: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logging.error(f"配置文件格式错误: {e}")
            raise
    
    def validate_config(self):
        """验证配置文件的必要字段"""
        if not self.config:
            raise ValueError("配置文件为空")
            
        required_sections = ['ali_baillan', 'rss_sources', 'crawler']
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"配置文件缺少必要字段: {section}")
        
        # 验证阿里百炼配置
        ali_config = self.config['ali_baillan']
        if not ali_config.get('api_key'):
            raise ValueError("阿里百炼配置缺少api_key")
        if not ali_config.get('endpoint'):
            # 设置默认endpoint
            ali_config['endpoint'] = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
            logging.info("使用默认的阿里百炼API endpoint")
        
        # 验证RSS源配置
        if not isinstance(self.config['rss_sources'], list):
            raise ValueError("rss_sources必须是列表格式")
        if len(self.config['rss_sources']) == 0:
            raise ValueError("rss_sources列表不能为空")
            
        for source in self.config['rss_sources']:
            if 'url' not in source or 'name' not in source:
                raise ValueError("每个RSS源必须包含url和name字段")
        
        # 验证爬虫配置
        crawler_config = self.config['crawler']
        required_crawler_fields = ['max_articles', 'days_back', 'output_dir']
        for field in required_crawler_fields:
            if field not in crawler_config:
                raise ValueError(f"爬虫配置缺少必要字段: {field}")
    
    def _set_defaults(self):
        """设置可选字段的默认值"""
        crawler_config = self.config['crawler']
        
        if 'timeout' not in crawler_config:
            crawler_config['timeout'] = 10
        if 'retries' not in crawler_config:
            crawler_config['retries'] = 3
        if 'user_agent' not in crawler_config:
            crawler_config['user_agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        if 'request_delay' not in crawler_config:
            crawler_config['request_delay'] = 1.0

    def get_ali_baillan_config(self):
        """获取阿里百炼API配置"""
        return self.config['ali_baillan']
    
    def get_rss_sources(self):
        """获取RSS源列表"""
        return self.config['rss_sources']
    
    def get_crawler_config(self):
        """获取爬虫配置"""
        return self.config['crawler']


# ==========================================
# 5. RSS解析器
# ==========================================
class RSSParser:
    """RSS/Atom源解析器"""

    def __init__(self, days_back=7, timeout=20):
        """
        初始化RSS解析器
        
        Args:
            days_back (int): 获取多少天内的文章
            timeout (int): 请求超时时间
        """
        self.days_back = days_back
        self.cutoff_date = datetime.now() - timedelta(days=days_back)
        self.timeout = timeout
    
    def parse_feed(self, feed_url, source_name, source_type):
        """
        解析单个RSS/Atom源
        
        Args:
            feed_url (str): RSS源URL
            source_name (str): 源名称
            source_type (str): 源类型
            
        Returns:
            list: 文章列表
        """
        articles = []
        try:
            logging.info(f"正在解析RSS源: {source_name} ({feed_url})")
            
            # 使用User-Agent避免被某些源拒绝
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; AI-News-Crawler/1.0)'}
            
            feed = feedparser.parse(feed_url, request_headers=headers)
            
            if feed.bozo:
                # 即使有警告，也尝试继续解析
                logging.warning(f"RSS源解析警告: {source_name} - {feed.bozo_exception}")
            
            if not feed.entries:
                logging.warning(f"RSS源 {source_name} 没有获取到任何条目")
                return []
            
            for entry in feed.entries:
                # 提取发布时间
                published = self._extract_published_date(entry)
                
                # 如果没有发布时间，或者时间太旧，则跳过（除非是强制抓取）
                if published and published < self.cutoff_date:
                    continue
                
                # 提取文章信息
                article = {
                    'title': self._clean_text(entry.get('title', '')),
                    'link': self._extract_link(entry),
                    'published': published or datetime.now(), # 默认为当前时间
                    'summary': self._clean_text(entry.get('summary', entry.get('description', ''))),
                    'source_name': source_name,
                    'source_type': source_type,
                    'raw_content': self._extract_content(entry),
                    'tags': self._extract_tags(entry)
                }
                
                # 如果summary为空，尝试从content提取
                if not article['summary'] and article['raw_content']:
                    article['summary'] = TextNormalizer.clean_html(article['raw_content'])[:300]
                
                # 如果标题为空，跳过
                if not article['title']:
                    continue
                    
                articles.append(article)
            
            logging.info(f"从 {source_name} 获取到 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            logging.error(f"解析RSS源失败 {source_name}: {e}", exc_info=True)
            return []
    
    def _extract_link(self, entry):
        """提取链接，处理某些RSS源中链接在href属性的情况"""
        link = entry.get('link')
        if not link:
            # 尝试从links数组中找
            links = entry.get('links', [])
            if links:
                link = links[0].get('href')
        return link if link else ""

    def _extract_published_date(self, entry):
        """从RSS条目中提取发布时间"""
        # 优先解析结构化时间
        time_fields = ['published_parsed', 'updated_parsed']
        for field in time_fields:
            if hasattr(entry, field) and getattr(entry, field):
                parsed_time = getattr(entry, field)
                try:
                    return datetime(*parsed_time[:6])
                except (TypeError, ValueError):
                    pass
        
        # 尝试解析字符串时间
        str_fields = ['published', 'updated', 'created', 'date']
        for field in str_fields:
            if hasattr(entry, field) and getattr(entry, field):
                date_str = getattr(entry, field)
                # 尝试常见格式
                formats = [
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%dT%H:%M:%S%z',
                    '%Y-%m-%d %H:%M:%S',
                    '%a, %d %b %Y %H:%M:%S %Z',
                    '%a, %d %b %Y %H:%M:%S %z'
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
        return None

    def _extract_content(self, entry):
        """提取文章内容"""
        if 'content' in entry and entry['content']:
            return entry['content'][0].get('value', '')
        if 'summary' in entry and entry['summary']:
            return entry['summary']
        return ""

    def _extract_tags(self, entry):
        """提取标签"""
        tags = []
        if 'tags' in entry:
            tags = [tag.get('term') for tag in entry['tags'] if tag.get('term')]
        return tags

    def _clean_text(self, text):
        """清理文本"""
        return TextNormalizer.clean_html(text)


# ==========================================
# 6. 内容下载器
# ==========================================
class ContentDownloader:
    """文章内容下载器，支持重试和代理"""

    def __init__(self, timeout=10, retries=3, user_agent=None):
        """
        初始化内容下载器
        
        Args:
            timeout (int): 请求超时时间
            retries (int): 重试次数
            user_agent (str): User-Agent字符串
        """
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        
        headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        self.session.headers.update(headers)
    
    def download_content(self, url):
        """
        下载文章完整内容
        
        Args:
            url (str): 文章URL
            
        Returns:
            str: 文章主要内容文本
        """
        for attempt in range(self.retries):
            try:
                logging.debug(f"正在下载文章内容: {url} (尝试 {attempt + 1}/{self.retries})")
                
                response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                response.raise_for_status()
                
                # 自动检测编码
                if response.encoding is None or response.encoding == 'ISO-8859-1':
                    response.encoding = response.apparent_encoding
                
                return self._extract_main_content(response.text, url)
                
            except requests.exceptions.SSLError:
                logging.warning(f"SSL错误，尝试忽略验证: {url}")
                # 可以在这里添加verify=False的逻辑，但为了安全起见，通常不推荐
                return ""
            except requests.exceptions.Timeout:
                logging.warning(f"请求超时: {url}")
                if attempt < self.retries - 1:
                    time.sleep(2 ** attempt)
            except requests.exceptions.RequestException as e:
                logging.warning(f"下载失败 (尝试 {attempt + 1}): {url} - {e}")
                if attempt < self.retries - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                logging.error(f"未知错误: {url} - {e}")
                break
        
        return ""

    def _extract_main_content(self, html, url):
        """
        从HTML中提取主要内容
        
        Args:
            html (str): HTML字符串
            url (str): 页面URL，用于特定网站的定制解析
            
        Returns:
            str: 提取的文本内容
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除干扰元素
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
            element.decompose()
        
        # 针对特定网站的定制解析逻辑
        main_content = None
        
        # ArXiv 特殊处理
        if 'arxiv.org' in url:
            main_content = soup.find('div', class_='ltx_page_main')
        
        # OpenAI Blog 特殊处理
        elif 'openai.com' in url:
            main_content = soup.find('div', class_='f-body-1')
            
        # 通用策略：寻找常见的文章容器
        if not main_content:
            selectors = [
                'article',
                'main',
                '[role="main"]',
                '.post-content',
                '.entry-content',
                '.article-content',
                '.content',
                '#content',
                '.post-body',
                '.markdown-body'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    # 选择内容最长的那个容器
                    main_content = max(elements, key=lambda e: len(e.get_text()))
                    break
        
        # 如果还是找不到，使用body
        if not main_content:
            main_content = soup.find('body')
        
        if main_content:
            text = main_content.get_text(separator='\n')
            text = TextNormalizer.normalize_whitespace(text)
            # 限制长度，避免处理过慢或超出API限制
            return TextNormalizer.truncate_text(text, max_length=8000)
        
        return ""


# ==========================================
# 7. 阿里百炼API客户端
# ==========================================
class AliBaillanAPIClient:
    """阿里百炼API客户端，用于生成摘要"""

    def __init__(self, api_key, endpoint):
        """
        初始化阿里百炼API客户端
        
        Args:
            api_key (str): API密钥
            endpoint (str): API端点URL
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def generate_summary(self, content, title="", max_tokens=500):
        """
        调用阿里百炼API生成内容摘要
        
        Args:
            content (str): 原始内容
            title (str): 文章标题
            max_tokens (int): 最大生成token数
            
        Returns:
            str: 生成的摘要文本
        """
        if not content or len(content.strip()) < 50:
            return "内容过短，无法生成有效摘要。"
        
        # 截断过长的内容输入，节省Token
        input_content = TextNormalizer.truncate_text(content, 4000)
        
        # 构建提示词
        system_prompt = "你是一个专业的科技新闻编辑，擅长将长篇文章总结为精炼的中文摘要。"
        user_prompt = f"请阅读以下文章，并生成一段200-300字的中文摘要。摘要应包含文章的核心观点和关键信息。\n\n标题：{title}\n\n正文：\n{input_content}"
        
        payload = {
            "model": "qwen-max",  # 使用通义千问最大模型
            "input": {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            },
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": 0.3,  # 降低温度以获得更确定的摘要
                "top_p": 0.8
            }
        }
        
        try:
            logging.info(f"正在调用阿里百炼API生成摘要 (标题: {title[:20]}...)")
            response = self.session.post(
                self.endpoint,
                json=payload,
                timeout=60  # API调用可能较慢
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 检查API返回状态
            if result.get('code') and result['code'] != 'Success':
                error_msg = result.get('message', '未知错误')
                logging.error(f"API返回错误: {error_msg}")
                return f"摘要生成失败：API错误 - {error_msg}"
            
            if 'output' in result and 'text' in result['output']:
                summary = result['output']['text'].strip()
                # 清理可能出现的markdown标记
                summary = re.sub(r'^#+\s*', '', summary)
                logging.info("摘要生成成功")
                return summary
            else:
                logging.error(f"API响应格式异常: {result}")
                return "摘要生成失败：响应格式异常"
                
        except requests.exceptions.Timeout:
            logging.error("API调用超时")
            return "摘要生成失败：请求超时"
        except requests.exceptions.RequestException as e:
            logging.error(f"API调用网络错误: {e}")
            return f"摘要生成失败：网络错误"
        except Exception as e:
            logging.error(f"摘要生成异常: {e}", exc_info=True)
            return f"摘要生成失败：{str(e)}"


# ==========================================
# 8. Markdown生成器
# ==========================================
class MarkdownGenerator:
    """Markdown文件生成器，生成Jekyll兼容格式"""

    def __init__(self, output_dir="./_posts"):
        """
        初始化Markdown生成器
        
        Args:
            output_dir (str): 输出目录
        """
        self.output_dir = output_dir
        self.ensure_output_dir()
    
    def ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
                logging.info(f"创建输出目录: {self.output_dir}")
            except OSError as e:
                logging.error(f"无法创建目录 {self.output_dir}: {e}")
                raise
    
    def generate_filename(self, title, date):
        """
        生成Markdown文件名 (Jekyll格式: YYYY-MM-DD-title.md)
        
        Args:
            title (str): 文章标题
            date (datetime): 发布日期
            
        Returns:
            str: 文件名
        """
        # 转换标题为安全的文件名
        # 移除或替换特殊字符
        clean_title = title.lower()
        clean_title = re.sub(r'[^\w\s-]', '', clean_title)  # 移除非单词字符
        clean_title = re.sub(r'[-\s]+', '-', clean_title).strip('-')  # 替换空格和连字符
        
        # 限制长度
        clean_title = clean_title[:80]
        
        date_str = date.strftime('%Y-%m-%d')
        return f"{date_str}-{clean_title}"
    
    def generate_front_matter(self, article_data):
        """
        生成Jekyll Front Matter
        
        Args:
            article_data (dict): 包含title, date, categories, tags, source_name等
            
        Returns:
            str: Front Matter字符串
        """
        date = article_data.get('published', datetime.now())
        # Jekyll日期格式通常包含时区
        date_str = date.strftime('%Y-%m-%d %H:%M:%S +0800')
        
        title = article_data.get('title', 'Untitled')
        # 转义YAML中的双引号
        title = title.replace('"', '\\"')
        
        categories = article_data.get('categories', ['AI新闻'])
        tags = article_data.get('tags', [])
        
        # 添加来源作为标签
        source = article_data.get('source_name', 'Unknown')
        if source not in tags:
            tags.append(source)
            
        front_matter = "---\n"
        front_matter += f"layout: post\n"
        front_matter += f"title: \"{title}\"\n"
        front_matter += f"date: {date_str}\n"
        
        # 处理列表类型的YAML
        front_matter += f"categories: {json.dumps(categories, ensure_ascii=False)}\n"
        front_matter += f"tags: {json.dumps(tags, ensure_ascii=False)}\n"
        
        # 添加自定义元数据
        front_matter += f"source: {source}\n"
        front_matter += f"source_url: {article_data.get('link', '')}\n"
        
        front_matter += "---\n\n"
        
        return front_matter
    
    def generate_markdown_content(self, article_data, ai_summary, original_content):
        """
        生成完整的Markdown内容
        
        Args:
            article_data (dict): 文章元数据
            ai_summary (str): AI生成的摘要
            original_content (str): 原文内容
            
        Returns:
            str: 完整的Markdown内容
        """
        # 生成Front Matter
        front_matter = self.generate_front_matter(article_data)
        
        # 生成正文
        content = front_matter
        
        # 添加AI摘要部分
        content += "## 🤖 AI 摘要\n\n"
        content += f"{ai_summary}\n\n"
        content += "---\n\n"
        
        # 添加原文部分
        content += "## 📄 原文概要\n\n"
        
        # 如果原文太长，只显示一部分
        preview_length = 2000
        if len(original_content) > preview_length:
            content += original_content[:preview_length]
            content += f"\n\n... (内容过长，已截断，共 {len(original_content)} 字) ...\n\n"
        else:
            content += original_content + "\n\n"
            
        # 添加原文链接
        content += "## 🔗 阅读原文\n\n"
        content += f"[点击查看原文]({article_data.get('link', '#')})\n"
        
        return content


# ==========================================
# 9. 去重检查器
# ==========================================
class DuplicateChecker:
    """内容去重检查器，基于MD5哈希和URL"""

    def __init__(self, cache_file="crawler_cache.json"):
        """
        初始化去重检查器
        
        Args:
            cache_file (str): 缓存文件路径
        """
        self.cache_file = cache_file
        self.cache = self.load_cache()
    
    def load_cache(self):
        """加载缓存文件"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"缓存文件加载失败: {e}，将创建新缓存")
        return {}
    
    def save_cache(self):
        """保存缓存到文件"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logging.error(f"缓存文件保存失败: {e}")
    
    def get_article_hash(self, article):
        """
        计算文章的唯一标识哈希
        结合标题和链接，因为同一篇文章可能有不同的URL参数，或者同一URL标题变了
        """
        title = article.get('title', '')
        link = article.get('link', '')
        # 规范化URL：移除查询参数和锚点
        clean_link = re.sub(r'[?#].*$', '', link)
        
        identifier = f"{title}|{clean_link}"
        return hashlib.md5(identifier.encode('utf-8')).hexdigest()
    
    def is_duplicate(self, article):
        """
        检查文章是否已处理
        
        Args:
            article (dict): 文章对象
            
        Returns:
            bool: 是否重复
        """
        article_hash = self.get_article_hash(article)
        return article_hash in self.cache
    
    def mark_as_processed(self, article):
        """
        标记文章为已处理
        
        Args:
            article (dict): 文章对象
        """
        article_hash = self.get_article_hash(article)
        self.cache[article_hash] = {
            'title': article.get('title'),
            'link': article.get('link'),
            'processed_at': datetime.now().isoformat(),
            'source': article.get('source_name')
        }
        # 每次更新都保存，防止程序崩溃导致丢失
        self.save_cache()


# ==========================================
# 10. 文件管理器
# ==========================================
class FileManager:
    """文件管理器，负责文件的安全写入"""

    def __init__(self, output_dir="./_posts"):
        self.output_dir = output_dir
        self.ensure_directory()
    
    def ensure_directory(self):
        """确保目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def save_markdown_file(self, filename, content):
        """
        保存Markdown文件
        
        Args:
            filename (str): 文件名
            content (str): 文件内容
            
        Returns:
            str: 保存的文件路径，失败返回None
        """
        # 确保文件名以.md结尾
        if not filename.endswith('.md'):
            filename += '.md'
            
        filepath = os.path.join(self.output_dir, filename)
        
        # 处理文件名冲突
        counter = 1
        original_filepath = filepath
        while os.path.exists(filepath):
            base, ext = os.path.splitext(original_filepath)
            filepath = f"{base}-{counter}{ext}"
            counter += 1
            
        try:
            # 使用原子写入模式（先写临时文件，再重命名）
            temp_filepath = filepath + '.tmp'
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 重命名
            os.replace(temp_filepath, filepath)
            
            logging.info(f"文件保存成功: {filepath}")
            return filepath
        except IOError as e:
            logging.error(f"文件保存失败: {filepath} - {e}")
            return None


# ==========================================
# 11. Sitemap生成器 (辅助功能)
# ==========================================
class SitemapGenerator:
    """生成简单的Sitemap用于SEO"""

    def __init__(self, output_dir, base_url="https://yourblog.com"):
        self.output_dir = output_dir
        self.base_url = base_url.rstrip('/')

    def update_sitemap(self):
        """扫描_posts目录并更新sitemap.xml"""
        posts_dir = os.path.join(self.output_dir, "_posts")
        if not os.path.exists(posts_dir):
            return

        urls = []
        # 匹配 Jekyll 文件名格式 YYYY-MM-DD-title.md
        pattern = re.compile(r'^(\d{4}-\d{2}-\d{2})-(.+)\.md$')
        
        for filename in os.listdir(posts_dir):
            match = pattern.match(filename)
            if match:
                date_str = match.group(1)
                slug = match.group(2)
                # Jekyll URL格式通常是 /year/month/day/slug.html
                url_path = f"/{date_str.replace('-', '/')}/{slug}.html"
                urls.append(f"{self.base_url}{url_path}")
        
        sitemap_content = '\n'
        sitemap_content += '\n'
        for url in urls:
            sitemap_content += f'  \n    {url}\n  \n'
        sitemap_content += ''
        
        sitemap_path = os.path.join(self.output_dir, "sitemap.xml")
        try:
            with open(sitemap_path, 'w', encoding='utf-8') as f:
                f.write(sitemap_content)
            logging.info(f"Sitemap已更新: {sitemap_path}")
        except Exception as e:
            logging.error(f"更新Sitemap失败: {e}")


# ==========================================
# 12. 主爬虫类
# ==========================================
class AINewsCrawler:
    """AI新闻爬虫主类，协调所有组件"""

    def __init__(self, config_manager):
        """
        初始化AI新闻爬虫
        
        Args:
            config_manager (ConfigManager): 配置管理器实例
        """
        self.config_manager = config_manager
        self.crawler_config = config_manager.get_crawler_config()
        
        # 初始化组件
        self.rss_parser = RSSParser(
            days_back=self.crawler_config['days_back'],
            timeout=self.crawler_config.get('timeout', 20)
        )
        
        self.content_downloader = ContentDownloader(
            timeout=self.crawler_config.get('timeout', 10),
            retries=self.crawler_config.get('retries', 3),
            user_agent=self.crawler_config.get('user_agent')
        )
        
        ali_config = config_manager.get_ali_baillan_config()
        self.ali_client = AliBaillanAPIClient(
            ali_config['api_key'],
            ali_config['endpoint']
        )
        
        self.markdown_gen = MarkdownGenerator(output_dir=self.crawler_config['output_dir'])
        self.dupe_checker = DuplicateChecker()
        self.file_manager = FileManager(output_dir=self.crawler_config['output_dir'])
        
        # 限流器
        self.rate_limiter = RateLimiter(min_interval=self.crawler_config.get('request_delay', 1.0))
        
        # 统计信息
        self.stats = {
            'total_fetched': 0,
            'downloaded': 0,
            'summarized': 0,
            'saved': 0,
            'skipped_duplicate': 0,
            'skipped_error': 0
        }
        
        # 注册信号处理，优雅退出
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        self._running = True

    def _signal_handler(self, signum, frame):
        """处理中断信号"""
        logging.info(f"接收到退出信号 {signum}，正在停止爬虫...")
        self._running = False

    def process_article(self, article):
        """
        处理单篇文章：下载、摘要、保存
        
        Args:
            article (dict): 文章数据
            
        Returns:
            bool: 是否处理成功
        """
        if not self._running:
            return False
            
        # 1. 检查去重
        if self.dupe_checker.is_duplicate(article):
            logging.info(f"跳过重复文章: {article['title']}")
            self.stats['skipped_duplicate'] += 1
            return False
        
        # 2. 下载完整内容
        # 如果RSS中已经有完整内容且足够长，可以跳过下载（可选逻辑）
        if not article.get('raw_content') or len(article['raw_content']) < 200:
            logging.info(f"下载内容: {article['title']}")
            article['content'] = self.content_downloader.download_content(article['link'])
            self.rate_limiter.wait() # 限流
        else:
            article['content'] = TextNormalizer.clean_html(article['raw_content'])
            
        if not article['content']:
            logging.warning(f"无法获取内容，跳过: {article['title']}")
            self.stats['skipped_error'] += 1
            return False
            
        self.stats['downloaded'] += 1
        
        # 3. 生成AI摘要
        logging.info(f"生成摘要: {article['title']}")
        ai_summary = self.ali_client.generate_summary(
            article['content'],
            article['title']
        )
        
        if not ai_summary or "失败" in ai_summary:
            logging.warning(f"摘要生成失败，使用默认摘要: {article['title']}")
            ai_summary = article.get('summary', '暂无摘要')[:200]
        
        self.stats['summarized'] += 1
        
        # 4. 生成标签
        tags = self._generate_tags(article, ai_summary)
        article['tags'] = tags
        
        # 5. 生成Markdown并保存
        try:
            markdown_content = self.markdown_gen.generate_markdown_content(
                article_data=article,
                ai_summary=ai_summary,
                original_content=article['content']
            )
            
            filename = self.markdown_gen.generate_filename(
                article['title'],
                article['published']
            )
            
            saved_path = self.file_manager.save_markdown_file(filename, markdown_content)
            
            if saved_path:
                self.dupe_checker.mark_as_processed(article)
                self.stats['saved'] += 1
                return True
            else:
                return False
                
        except Exception as e:
            logging.error(f"处理文章保存时出错: {article['title']} - {e}")
            self.stats['skipped_error'] += 1
            return False

    def _generate_tags(self, article, ai_summary):
        """根据内容生成标签"""
        tags = article.get('tags', []) # RSS自带的标签
        
        # 确保有基础标签
        if "AI" not in tags:
            tags.append("AI")
            
        content = (article['title'] + " " + (article.get('summary', '')) + " " + ai_summary).lower()
        
        # 关键词映射
        keywords_map = {
            'machine learning': '机器学习',
            'deep learning': '深度学习',
            'llm': '大模型',
            'gpt': 'GPT',
            'transformer': 'Transformer',
            'nlp': '自然语言处理',
            'computer vision': '计算机视觉',
            'reinforcement learning': '强化学习',
            'robot': '机器人',
            'generative': '生成式AI',
            'openai': 'OpenAI',
            'google': 'Google',
            'deepmind': 'DeepMind',
            'arxiv': 'ArXiv',
            'chatgpt': 'ChatGPT',
            'diffusion': '扩散模型',
            'multimodal': '多模态',
            'agent': '智能体'
        }
        
        for keyword, tag in keywords_map.items():
            if keyword in content and tag not in tags:
                tags.append(tag)
        
        # 限制标签数量
        return tags[:8]

    def run(self):
        """运行爬虫主流程"""
        logging.info("=" * 50)
        logging.info("AI News Crawler 启动")
        logging.info(f"配置: 最大文章数={self.crawler_config['max_articles']}, "
                    f"天数范围={self.crawler_config['days_back']}, "
                    f"输出目录={self.crawler_config['output_dir']}")
        logging.info("=" * 50)
        
        rss_sources = self.config_manager.get_rss_sources()
        
        for source in rss_sources:
            if not self._running:
                logging.info("收到停止信号，停止处理新的RSS源。")
                break
                
            if self.stats['saved'] >= self.crawler_config['max_articles']:
                logging.info(f"已达到最大文章保存数量限制: {self.crawler_config['max_articles']}")
                break
            
            logging.info(f"开始处理源: {source['name']}")
            
            # 解析RSS
            articles = self.rss_parser.parse_feed(
                source['url'],
                source['name'],
                source.get('type', 'news')
            )
            
            self.stats['total_fetched'] += len(articles)
            
            # 处理每篇文章
            for article in articles:
                if not self._running:
                    break
                    
                if self.stats['saved'] >= self.crawler_config['max_articles']:
                    break
                
                self.process_article(article)
                
                # 文章间延迟
                self.rate_limiter.wait()
            
            # 源间延迟
            time.sleep(2)
        
        # 结束统计
        logging.info("=" * 50)
        logging.info("爬虫任务完成!")
        logging.info(f"统计信息:")
        logging.info(f"  - 获取文章总数: {self.stats['total_fetched']}")
        logging.info(f"  - 成功下载内容: {self.stats['downloaded']}")
        logging.info(f"  - 成功生成摘要: {self.stats['summarized']}")
        logging.info(f"  - 成功保存文章: {self.stats['saved']}")
        logging.info(f"  - 跳过重复文章: {self.stats['skipped_duplicate']}")
        logging.info(f"  - 跳过错误文章: {self.stats['skipped_error']}")
        logging.info("=" * 50)
        
        # 可选：更新Sitemap
        # sitemap_gen = SitemapGenerator(self.crawler_config['output_dir'])
        # sitemap_gen.update_sitemap()


# ==========================================
# 13. 主入口
# ==========================================
def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='AI News Crawler - 自动化AI领域新闻聚合与Jekyll文章生成工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python ai_news_crawler.py --config config.yaml
  python ai_news_crawler.py -c config.yaml -l DEBUG
        """
    )
    
    parser.add_argument('--config', '-c', required=True, help='配置文件路径 (YAML格式)')
    parser.add_argument('--log-level', '-l', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='设置日志级别 (默认: INFO)')
    
    args = parser.parse_args()
    
    # 初始化日志
    LoggerManager.setup_logging(log_level=args.log_level)
    
    try:
        # 加载配置
        logging.info(f"正在加载配置文件: {args.config}")
        config_manager = ConfigManager(args.config)
        
        # 创建并运行爬虫
        crawler = AINewsCrawler(config_manager)
        crawler.run()
        
        logging.info("程序执行完毕，退出码 0")
        sys.exit(0)
        
    except FileNotFoundError as e:
        logging.error(f"配置文件错误: {e}")
        sys.exit(1)
    except ValueError as e:
        logging.error(f"配置验证失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("用户手动中断程序")
        sys.exit(1)
    except Exception as e:
        logging.error(f"程序发生未捕获的异常: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
博客最新文章自动邮件推送脚本

功能说明：
1. 从本地`_posts`目录获取最新发布的Markdown文件（按日期排序）
2. 提取文章标题和摘要内容
3. 使用环境变量配置的SMTP信息发送邮件通知订阅者
4. 完全遵循安全规范，敏感信息通过环境变量注入

使用方式：
- 本地测试：创建`.env`文件并安装`python-dotenv`
- GitHub Actions：通过secrets注入环境变量
- 定时任务：配合cron表达式实现周期性执行

依赖库：
- python-dotenv: 环境变量加载（仅本地开发需要）
"""

import os
import re
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 配置日志系统
logging.basicConfig(level=logging.INFO)

def mail_generator() -> tuple[str, str]:
    """
    从本地`_posts`目录获取最新发布的Markdown文件内容
    
    按照文件名中的日期（YYYY-MM-DD格式）排序，取最新的文件
    """
    try:
        # 获取_posts目录下的所有.md文件
        posts_dir = os.path.join(os.path.dirname(__file__), "_posts")
        assert os.path.exists(posts_dir), "_posts目录不存在"
        md_files = [f for f in os.listdir(posts_dir) if f.endswith(".md")]  # 注意这行代码
        assert md_files, "_posts目录中没有找到Markdown文件"
        
        # 按日期排序（从文件名中提取YYYY-MM-DD）并取最新的文件
        # 重写排序函数
        def extract_date(filename)->str:
            # 尝试提取YYYY-MM-DD格式的日期
            match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
            assert match, "提取日期为空"
            return match.group(1)
        md_files.sort(key=extract_date, reverse=True)
        latest_file = md_files[0]
        file_path = os.path.join(posts_dir, latest_file)

        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logging.info(f"已读取最新文章: {latest_file}")

        # 提取文章标题（支持Jekyll/YAML front matter）
        re_content = re.search(r'title:\s*[\'\"]?(.+?)[\'\"]?\s*$', content, re.MULTILINE)
        if re_content:
            title = re_content.group(1).strip()
        else:
            # 如果没有YAML格式中的标题，则尝试从原文获得标题
            h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = h1_match.group(1).strip() if h1_match else "未命名文章"
        body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)
        title = f"文章：{title}生成成功"
        body = f"""来自 https://github.com/axwhizee/axwhizee.github.io 的最新文章已生成成功！
时间：{datetime.now().strftime('%Y年%m月%d日')}\n全文如下：
""" + f"<div>{'-'*10}\n{body}\n{'-'*10}</div>"
        return title, body
    except Exception as e:
        logging.error(f"读取最新文章时发生错误: {e}")
        raise


def send_email(to_email: str, subject: str, body: str) -> None:
    """ 
    使用SMTP协议发送电子邮件
    
    凭证信息从环境变量读取，确保安全性
    
    Args:
        to_email (str): 收件人邮箱地址
        subject (str): 邮件主题
        body (str): 邮件正文内容
    
    Returns:
        bool: 发送成功返回True，否则False
    """
    # 从环境变量读取SMTP配置
    smtp_server = os.getenv("SMTP_SERVER") or SMTP_SERVER
    sender_email = os.getenv("EMAIL_USER") or EMAIL_USER
    password = os.getenv("EMAIL_PASSWORD") or EMAIL_PASSWORD

    # 类型收窄
    try:
        assert smtp_server, "缺少: SMTP_SERVER"
        assert sender_email, "缺少: EMAIL_USER"
        assert password, "缺少: EMAIL_PASSWORD"
    except Exception as e:
        logging.error(f"SMTP配置不完整或无效: {e}")
        raise

    # 构建邮件内容
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # 发送邮件
    try:
        logging.info(f"正在连接SMTP服务器 {smtp_server}")
        try:    # 先尝试SSL连接，如果失败再尝试TLS（STARTTLS）连接
            with smtplib.SMTP_SSL(smtp_server, 465, timeout=10) as server:
                server.login(sender_email, password)
                server.sendmail(sender_email, to_email, msg.as_string())
        except:
            logging.info("SSL连接失败，改用TLS连接...")
            with smtplib.SMTP(smtp_server, 587, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(sender_email, password)
                server.sendmail(sender_email, to_email, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        logging.error("❌ SMTP认证失败，请检查邮箱账号和授权码是否正确")
        raise
    except smtplib.SMTPConnectError:
        logging.error("❌ 无法连接到SMTP服务器，请检查服务器地址和端口配置")
        raise
    except Exception as e:
        logging.error(f"❌ 发送邮件时发生异常: {e}")
        raise
    logging.info("✅ 邮件发送成功")


if __name__ == "__main__":
    SMTP_SERVER = None
    EMAIL_USER = None
    EMAIL_PASSWORD = None
    RECIPIENT_EMAIL = None

    logging.info("🚀 开始执行博客最新文章邮件推送任务")

    # 获取最新文章内容
    logging.info("正在从本地 _posts 目录获取最新文章...")
    subject, body = mail_generator()
    
    # 发送邮件
    to_email=os.getenv("RECIPIENT_EMAIL") or RECIPIENT_EMAIL
    assert to_email, "缺少环境变量: RECIPIENT_EMAIL"
    send_email(to_email, subject=subject, body=body)
    # print(f"From: {EMAIL_USER}\nTo: {to_email}:\n{body}")

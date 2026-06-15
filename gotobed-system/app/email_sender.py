import smtplib
from datetime import datetime
from zoneinfo import ZoneInfo
from email.mime.text import MIMEText

from flask import current_app

# 北京时间
BJT = ZoneInfo('Asia/Shanghai')

# 中文星期映射
_WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']


def get_beijing_time():
    now = datetime.now(BJT)
    weekday = _WEEKDAYS[now.weekday()]
    return now.strftime(f'%Y-%m-%d {weekday} %H:%M')


def send_email(subject: str, content: str, to_address: str):
    """发送邮件通知，配置从 Flask app config 读取"""
    if not to_address:
        print(f'未配置邮箱，跳过邮件发送。结果：{content}')
        return

    smtp_host = current_app.config.get('SMTP_HOST', '')
    smtp_port = current_app.config.get('SMTP_PORT', 465)
    smtp_user = current_app.config.get('SMTP_USER', '')
    smtp_pass = current_app.config.get('SMTP_PASS', '')

    if not smtp_user or not smtp_pass:
        print(f'SMTP 未配置，跳过邮件发送。结果：{content}')
        return

    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = smtp_user
    msg['To'] = to_address
    msg['Subject'] = subject

    try:
        smtp = smtplib.SMTP_SSL(smtp_host, smtp_port)
        smtp.login(smtp_user, smtp_pass)
        smtp.sendmail(smtp_user, to_address, msg.as_string())
        smtp.quit()
        print(f'邮件发送成功 -> {to_address}')
    except Exception as e:
        print(f'邮件发送失败: {e}')


def send_gotobed_result(content: str, to_address: str):
    """发送查寝结果通知"""
    formatted_date = get_beijing_time()
    result_status = '✅成功' if '成功' in content else '❌失败'
    subject = f'查寝 {result_status} {formatted_date}'
    body = f'签到结果：{content}'
    send_email(subject, body, to_address)

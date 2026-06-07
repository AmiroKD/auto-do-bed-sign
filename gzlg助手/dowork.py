#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 27/4/2024 下午9:55
# @Author : G5116
import re, execjs, json, requests, os, sys, socket, time, random
import dns.resolver

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
project_root = os.path.dirname(current_dir)
# 将项目根目录添加到 sys.path
sys.path.append(project_root)
from emailSender import send_QQ_email_plain

with open('gzlg助手/g5116.js', 'r', encoding='utf-8') as f:
    js = f.read()
ctx = execjs.compile(js)

# ---- 国内 DNS 解析配置 ----
TARGET_DOMAINS = {'ids.gzist.edu.cn', 'xsfw.gzist.edu.cn'}
CHINA_DNS_SERVERS = ['223.5.5.5', '119.29.29.29']
_dns_cache = {}
_original_getaddrinfo = socket.getaddrinfo


def _resolve_with_china_dns(hostname):
    """使用国内 DNS 服务器解析域名，带缓存"""
    if hostname in _dns_cache:
        return _dns_cache[hostname]
    for dns_server in CHINA_DNS_SERVERS:
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_server]
            resolver.lifetime = 5
            answers = resolver.resolve(hostname, 'A')
            ip = str(answers[0])
            _dns_cache[hostname] = ip
            print(f'DNS 解析: {hostname} -> {ip} (via {dns_server})')
            return ip
        except Exception as e:
            print(f'DNS 解析 {hostname} 失败 (via {dns_server}): {e}')
            continue
    raise RuntimeError(f'所有国内 DNS 服务器均无法解析 {hostname}')


def _custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """自定义 getaddrinfo，对目标域名使用国内 DNS 解析"""
    if host in TARGET_DOMAINS:
        ip = _resolve_with_china_dns(host)
        return _original_getaddrinfo(ip, port, family, type, proto, flags)
    return _original_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _custom_getaddrinfo


def init():
    session = requests.Session()
    session.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    return session


def getCode(image):
    # 自动打码 注册地址 免费300积分
    # https://console.jfbym.com/register/TG66434
    url = "http://api.jfbym.com/api/YmServer/customApi"
    payload = {
        "image": image,
        "token": str(os.getenv('TOKEN')),
        "type": "10110"
    }
    resp = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
    result = resp.json()["data"]["data"]
    result = result.replace('o', '0').replace('l', '1').replace('O', '0').replace('十', '+').replace('三', '')
    print("识别结果:", result[:-1])
    return eval(result[:-1])


def login(session):
    params = {'uid': ''}
    yzm_url = 'https://ids.gzist.edu.cn/lyuapServer/kaptcha'
    response = session.get(yzm_url, params=params)
    uid = response.json()['uid']
    yzm_base64 = re.search('base64,(.*)', response.json()['content']).group(1)
    yzm = getCode(yzm_base64)
    psw = ctx.call('G5116', os.getenv('USERNAME'), os.getenv('PASSWORD'), '')
    data = {
        'username': os.getenv('USERNAME'),
        'password': str(psw),
        'service': 'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/*default/index.do',
        'loginType': '',
        'id': uid,
        'code': str(yzm),
    }
    response = session.post('https://ids.gzist.edu.cn/lyuapServer/v1/tickets', data=data)
    if 'NOUSER' in response.json():
        result = '账号不存在'
        send_QQ_email_plain(result)
        sys.exit(1)
    elif 'PASSERROR' in response.json():
        result = '密码错误'
        send_QQ_email_plain(result)
        sys.exit(1)
    elif 'CODEFALSE' in response.json():
        result = '验证码错误'
        send_QQ_email_plain(result)
        sys.exit(1)
    else:
        return response.json()['ticket']


def UpdateCookie(session, ticket):
    params = {'ticket': ticket}
    response = session.get(
        'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/*default/index.do',
        params=params)
    session.cookies = response.cookies


def doWork(session):
    data = {
        'data': '{"APPID":"6390414391613368","APPNAME":"swmqdzsapp"}'
    }

    response = session.post(
        'https://xsfw.gzist.edu.cn/xsfw/sys/swpubapp/MobileCommon/getSelRoleConfig.do',
        cookies=session.cookies,
        data=data,
    )
    _WEU = response.cookies.get('_WEU')
    cookies = {
        '_WEU': _WEU
    }
    data_by = {
        'data': '{"SFFWN":"1","DDDM":"134D3343A40D51AFE0630717000A7549","DDMC":"广州理工学院白云区","QDJD":113.46617498988796,"QDWD":23.263957044502487,"RWBH":"16FC8C91BCDDEC67E0630717000A97E1","QDPL":"2"}',
    }
    data_hz = {
        'data': '{"SFFWN":"1","DDDM":"b2c1441606da4efbb9fe5b2b89226396","DDMC":"广州理工学院(博罗校区)","QDJD":114.08675193786623,"QDWD":23.186742693715477,"RWBH":"16FC8C91BCDDEC67E0630717000A97E1","QDPL":"2"}',
    }
    if int(os.getenv('USERNAME')[:4]) >= 2025:
        print('定位hz')
        response = session.post(
            'https://xsfw.gzist.edu.cn/xsfw/sys/swmqdzsapp/MobileJrqdController/doSignIn.do',
            cookies=cookies,
            data=data_hz,
        )
    else:
        print('定位by')
        response = session.post(
            'https://xsfw.gzist.edu.cn/xsfw/sys/swmqdzsapp/MobileJrqdController/doSignIn.do',
            cookies=cookies,
            data=data_by,
        )
    global result
    try:
        if response.json()['msg'] == '成功':
            result = response.json()['data']['prompt']
            print(result)
            return result
    except:
        result = '签到失败'
        return result


email_address = os.getenv('EMAIL_ADDRESS')


def main():
    session = init()
    ticket = login(session)
    UpdateCookie(session, ticket)
    res = doWork(session)
    send_QQ_email_plain(res)


if __name__ == '__main__':
    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        try:
            main()
            print("执行成功！")
            break
        except Exception as e:
            attempt += 1
            print(f"尝试 {attempt} 次失败，错误信息：{e}")
            if attempt == max_attempts:
                send_QQ_email_plain(f'连续' + str(max_attempts) + '次执行失败！请手动签到！')
                print("已达最大尝试次数，程序结束。")
            else:
                wait = min(5 * (2 ** (attempt - 1)), 60) + random.uniform(0, 3)
                print(f"等待 {wait:.1f} 秒后重试...")
                time.sleep(wait)

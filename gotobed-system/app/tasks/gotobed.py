#!/usr/bin/env python
# -*- coding: utf-8 -*-
import base64
import re
import json
import socket
import time
import random
import os
from datetime import datetime

import execjs
import requests
import ddddocr
import dns.resolver

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


# 替换系统的 DNS 解析函数
socket.getaddrinfo = _custom_getaddrinfo

# 加载 JS 加密脚本
_js_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'gzlg助手', 'g5116.js')
_js_path = os.path.normpath(_js_path)
with open(_js_path, 'r', encoding='utf-8') as f:
    _js_code = f.read()
_ctx = execjs.compile(_js_code)


def _init_session():
    session = requests.Session()
    session.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/91.0.4472.124 Safari/537.36"
    }
    return session


def _get_code(image_base64):
    """验证码 OCR 识别"""
    ocr = ddddocr.DdddOcr(show_ad=False)
    image_bytes = base64.b64decode(image_base64)
    result = ocr.classification(image_bytes)
    result = result.replace('o', '0').replace('l', '1').replace('O', '0').replace('十', '+').replace('三', '')
    print('验证码识别结果：' + result[:-1])
    ans = eval(result[:-1])
    print('计算结果：', ans)
    return ans


def _login(session, username, password, principal=None, credential=None):
    """登录学工平台，返回 ticket"""
    params = {'uid': ''}
    yzm_url = 'https://ids.gzist.edu.cn/lyuapServer/kaptcha'
    response = session.get(yzm_url, params=params)
    uid = response.json()['uid']

    yzm = None
    if 'content' in response.json() and response.json()['content']:
        yzm_match = re.search('base64,(.*)', response.json()['content'])
        if yzm_match:
            yzm_base64 = yzm_match.group(1)
            yzm = _get_code(yzm_base64)
            print('验证码：', yzm)

    psw = _ctx.call('G5116', username, password, '')
    data = {
        'username': username,
        'password': str(psw),
        'service': 'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/*default/index.do',
        'loginType': '',
        'id': uid,
    }

    if yzm is not None:
        data['code'] = str(yzm)

    response = session.post('https://ids.gzist.edu.cn/lyuapServer/v1/tickets', data=data)
    login_response = response.json()

    if 'NOUSER' in login_response:
        raise RuntimeError('账号不存在')
    elif 'PASSERROR' in login_response:
        raise RuntimeError('密码错误')
    elif 'CODEFALSE' in login_response:
        raise RuntimeError('验证码错误')

    print("登录响应：", login_response)

    # 二次验证
    if 'data' in response.json() and response.json()['data']['code'] == 'TWOVERIFY':
        if not principal or not credential:
            raise RuntimeError('需要二次验证，但未配置密保问题/答案')

        vcodes = response.json()['data']['uid']
        session.headers['vcodes'] = vcodes
        json_data = {
            'userName': username,
            'principal': principal,
            'credential': credential,
            'type': '2',
            'service': 'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/*default/index.do',
            'loginType': '',
            'isCommonIP': '',
        }
        session.post('https://ids.gzist.edu.cn/lyuapServer/login/twoVertify',
                     headers=session.headers, json=json_data)
        response = session.post('https://ids.gzist.edu.cn/lyuapServer/v1/tickets', data=data)
        return response.json()['ticket']

    return response.json()['ticket']


def _update_cookie(session, ticket):
    """使用 ticket 获取 cookie"""
    params = {'ticket': ticket}
    response = session.get(
        'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/*default/index.do',
        params=params)
    session.cookies = response.cookies


def _do_gotobed(session, username):
    """执行查寝签到"""
    data = {
        'data': '{"APPID":"5405362541914944","APPNAME":"swmzncqapp"}'
    }
    response = session.post(
        'https://xsfw.gzist.edu.cn/xsfw/sys/swpubapp/MobileCommon/getSelRoleConfig.do',
        cookies=session.cookies,
        data=data,
    )
    _WEU = response.cookies.get('_WEU')
    cookies = {'_WEU': _WEU}

    data_by = {
        'data': '{"SFFWN":"1","DDDM":"134D3343A40D51AFE0630717000A7549",'
                '"DDMC":"广州理工学院白云区","QDJD":113.46617498988796,'
                '"QDWD":23.263957044502487,"RWBH":"16FC8C91BCDDEC67E0630717000A97E1",'
                '"QDPL":"2"}',
    }
    data_hz = {
        'data': '{"SFFWN":"1","DDDM":"b2c1441606da4efbb9fe5b2b89226396",'
                '"DDMC":"广州理工学院(博罗校区)","QDJD":114.08675193786623,'
                '"QDWD":23.186742693715477,"RWBH":"16FC8C91BCDDEC67E0630717000A97E1",'
                '"QDPL":"2"}',
    }

    if int(username[:4]) >= datetime.now().year:
        print('定位hz')
        response = session.post(
            'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/modules/studentCheckController/uniFormSignUp.do',
            cookies=cookies, data=data_hz)
    else:
        print('定位by')
        response = session.post(
            'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/modules/studentCheckController/uniFormSignUp.do',
            cookies=cookies, data=data_by)

    try:
        result = response.json()['msg']
        print('签到结果: ' + result)
        return result
    except json.JSONDecodeError:
        print(f'签到异常: JSON解析错误，响应: {response.text}')
        return '查寝失败'
    except Exception as e:
        print(f'签到异常: {e}')
        return '查寝失败'


def run_gotobed(username: str, password: str,
                principal: str = None, credential: str = None,
                email: str = None) -> dict:
    """
    执行查寝任务，带重试。

    返回: {'status': 'success'|'failure', 'message': str}
    """
    from ..email_sender import send_gotobed_result

    max_attempts = 5
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            session = _init_session()
            ticket = _login(session, username, password, principal, credential)
            _update_cookie(session, ticket)
            result = _do_gotobed(session, username)

            if email:
                send_gotobed_result(result, email)

            return {'status': 'success', 'message': result}

        except Exception as e:
            last_error = str(e)
            print(f"尝试 {attempt} 次失败，错误信息：{e}")
            if attempt < max_attempts:
                wait = min(5 * (2 ** (attempt - 1)), 60) + random.uniform(0, 3)
                print(f"等待 {wait:.1f} 秒后重试...")
                time.sleep(wait)

    error_msg = f'连续{max_attempts}次执行失败: {last_error}'
    if email:
        send_gotobed_result(error_msg, email)
    return {'status': 'failure', 'message': error_msg}

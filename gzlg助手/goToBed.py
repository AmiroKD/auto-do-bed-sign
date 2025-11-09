#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 28/4/2024 下午8:33
# @Author : G5116
import re, execjs, json, requests, os, sys
from datetime import datetime
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


def init():
    session = requests.Session()
    session.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    return session


def getCode(image):
    # 自动打码 注册地址 免费300积分
    # https://console.jfbym.com/register
    url = "http://api.jfbym.com/api/YmServer/customApi"
    payload = {
        "image": image,
        "token": str(os.getenv('TOKEN')),
        "type": "10110"
    }
    resp = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
    result = resp.json()["data"]["data"]
    result = result.replace('o', '0').replace('l', '1').replace('O', '0').replace('十', '+').replace('三', '')
    # logging.log(logging.INFO, '验证码识别结果：' + result[:-1])
    print('验证码识别结果：' + result[:-1])
    ans = eval(result[:-1])
    print('计算结果：', ans)
    return ans


def login(session):
    params = {'uid': ''}
    yzm_url = 'https://ids.gzist.edu.cn/lyuapServer/kaptcha'
    response = session.get(yzm_url, params=params)
    uid = response.json()['uid']

    # 检查是否存在验证码
    yzm = None
    if 'content' in response.json() and response.json()['content']:
        # 存在验证码内容，尝试提取验证码
        yzm_match = re.search('base64,(.*)', response.json()['content'])
        if yzm_match:
            yzm_base64 = yzm_match.group(1)
            yzm = getCode(yzm_base64)
            print('验证码：', yzm)

    psw = ctx.call('G5116', os.getenv('USERNAME'), os.getenv('PASSWORD'), '')
    data = {
        'username': os.getenv('USERNAME'),
        'password': str(psw),
        'service': 'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/*default/index.do',
        'loginType': '',
        'id': uid,
    }
    
    # 只有在验证码存在时才添加code参数
    if yzm is not None:
        data['code'] = str(yzm)

    # 一次登陆
    response = session.post('https://ids.gzist.edu.cn/lyuapServer/v1/tickets', data=data)
    login_response = response.json()
    if 'NOUSER' in login_response:
        # logging.error('登录异常')
        print("登录失败，响应内容：", login_response)
        result = '账号不存在'
        send_QQ_email_plain(result)
        sys.exit(1)
    elif 'PASSERROR' in login_response:
        # logging.error('登录异常')
        print("登录失败，响应内容：", login_response)
        result = '密码错误'
        send_QQ_email_plain(result)
        sys.exit(1)
    elif 'CODEFALSE' in login_response:
        # logging.error('登录异常')
        print("登录失败，响应内容：", login_response)
        result = '验证码错误'
        send_QQ_email_plain(result)
        sys.exit(1)
    elif 'ticket' in login_response:
        # 打印完整的响应内容以供调试
        print("登录失败，响应内容：", login_response)
        send_QQ_email_plain("登录失败，请检查账号、密码或验证码。")
        sys.exit(1)
    else:
        print("登录响应：", login_response)

    # 判断登录是否需要二次验证
    if 'data' in response.json() and response.json()['data']['code'] == 'TWOVERIFY':
        # 需要二次验证
        vcodes = response.json()['data']['uid']
        session.headers['vcodes'] = vcodes
        json_data = {
            'userName': str(os.getenv('USERNAME')),
            'principal': os.getenv('PRINCIPAL'),
            'credential': os.getenv('CREDENTIAL'),
            'type': '2',
            'service': 'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/*default/index.do',
            'loginType': '',
            'isCommonIP': '',
        }
        session.post('https://ids.gzist.edu.cn/lyuapServer/login/twoVertify', headers=session.headers,
                     json=json_data)
        # 二次登陆
        response = session.post('https://ids.gzist.edu.cn/lyuapServer/v1/tickets', data=data)
        return response.json()['ticket']
    # 登录成功
    else:
        # logging.log(logging.INFO, '登录成功')
        return response.json()['ticket']


def UpdateCookie(session, ticket):
    params = {'ticket': ticket}
    response = session.get(
        'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/*default/index.do',
        params=params)
    session.cookies = response.cookies


def doWork(session):
    data = {
        'data': '{"APPID":"5405362541914944","APPNAME":"swmzncqapp"}'
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
    # logging.log(logging.INFO, '开始签到任务')
    if int(os.getenv('USERNAME')[:4]) >= datetime.now().year:
        print('定位hz')
        response = session.post(
            'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/modules/studentCheckController/uniFormSignUp.do',
            cookies=cookies,
            data=data_hz,
        )
    else:
        print('定位by')
        response = session.post(
            'https://xsfw.gzist.edu.cn/xsfw/sys/swmzncqapp/modules/studentCheckController/uniFormSignUp.do',
            cookies=cookies,
            data=data_by,
        )
    global result
    try:
        result = response.json()['msg']
        # logging.log(logging.INFO, '签到结果: ' + result)
        print('签到结果: ' + result)
        return result
    except:
        # logging.error('签到异常')
        print('签到异常')
        result = '查寝失败'
        return result


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
                send_QQ_email_plain(f'连续' + str(max_attempts) + '次执行失败！请手动查寝！')
                print("已达最大尝试次数，程序结束。")

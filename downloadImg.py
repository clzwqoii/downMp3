#-*- coding: utf-8 -*-
import time
from http import cookiejar
import requests
from bs4 import BeautifulSoup
import os
import pymysql
import json
__author__ = '小小·殇'
headers = {
    "Host": "console.lsfhxc.com",
    "Referer": "http://console.lsfhxc.com/auth/login",
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87'
}

# 使用登录cookie信息
session = requests.session()
session.cookies = cookiejar.LWPCookieJar(filename='cookies.txt')
try:
    print(session.cookies)
    session.cookies.load(ignore_discard=True)
except:
    print("还没有cookie信息")

db = pymysql.connect(
                    host='localhost',
                    port=3306,
                    user='root',
                    passwd='root',
                    db='test',
                    charset='utf8',
                )
cur = db.cursor()

def get_xsrf():
    response = session.get("http://console.lsfhxc.com/auth/login", headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    xsrf = soup.find('input', attrs={"name": "csrf_token"}).get("value")
    return xsrf


def get_captcha():
    """
    把验证码图片保存到当前目录，手动识别验证码
    :return:
    """
    t = str(int(time.time() * 1000))
    captcha_url = 'https://www.zhihu.com/captcha.gif?r=' + t + "&type=login"
    r = session.get(captcha_url, headers=headers)
    with open('captcha.jpg', 'wb') as f:
        f.write(r.content)
    captcha = input("验证码：")
    return captcha

def getInteractiveCount(interactiveId):
    response = session.get('http://console.lsfhxc.com/api/v1.0/getrocord/1?planid=' + str(interactiveId), headers=headers)
    result = response.json()
    interactiveCount = 0
    if (result['res'] == 'ok') & (result['status'] == 200):
        for i in range(len(result['results'])):
            if result['results'][i]['user'] == 'customer':
                interactiveCount += 1
    return interactiveCount

def login(email, password):
    login_url = 'http://console.lsfhxc.com/auth/login'
    data = {
        'email': email,
        'password': password,
        'csrf_token': get_xsrf()
        # "captcha": get_captcha(),
    }
    response = session.post(login_url, data=data, headers=headers)
    login_code = response.status_code
    print('状态码 : ' + str(login_code))
    for i in session.cookies:
        print(i)
    session.cookies.save()


def addData(result, j):
    try:
        interactiveId = result['results'][j]['_id']['$oid']
        interactiveCount = getInteractiveCount(interactiveId)
        tag = result['results'][j]['current_phoneres']['phoneprocessinfo']['restag']
        phoneNumber = result['results'][j]['phonenumber']
        cname = result['results'][j]['PhoneUserInfo']['cname']
        callTime = result['results'][j]['current_phoneres']['phoneprocessinfo']['time']
        lostDialTime = result['results'][j]['current_phoneres']['lastime']
        audioSrc = result['results'][j]['phonenumber'] + '_' + result['results'][j]['current_phoneres'][
            'micon'] + '.mp3'
        cur.execute("INSERT INTO bot_call(phone_info_name, phone_number, audio_src, call_time, lost_dial_time, `type`, interactive_count) VALUES ('%s', %d, '%s', '%s', %d, '%s', %d)" % (str(cname), int(phoneNumber), str(audioSrc), str(callTime), int(lostDialTime), str(tag), int(interactiveCount)))
        db.commit()
    except:
        print('addData fail : rollback')
        db.rollback()

def downloads(result, j, downloadsCount):
    audioUrl = 'http://console.lsfhxc.com/recordfile/' + result['results'][j]['current_phoneres']['micon'] + '/' + \
               result['results'][j]['phonenumber'] + '_' + result['results'][j]['current_phoneres']['micon'] + '.mp3'
    # req.encoding = 'gbk'
    print('download image:%s' % audioUrl)
    filename = os.path.basename(audioUrl)
    req = requests.get(audioUrl)
    with open(filename, 'wb') as code:
        downloadsCount += 1
        code.write(req.content)

def downloadsServer(downloadsCount, pageNumber, totalPageNumber):
    for i in range(totalPageNumber):
        if i == 0:
            response = session.get(
                'http://console.lsfhxc.com/api/v1.0/public?cnameandphone=&end=300&isdial=&pageNumber=' + str(i) + '&start=1',
                headers=headers)
        else:
            response = session.get(
                'http://console.lsfhxc.com/api/v1.0/public?cnameandphone=&end=' + str(300 + (i * pageNumber)) + '&isdial=&pageNumber=' + str(i) + '&start=' + str(1 + (i * pageNumber)),
                headers=headers)
        result = response.json()  # res.status_code     res.text
        if (result['res'] != 'ok') | (result['status'] != 200):
            print('error : pageNumber:' + str(i))
            continue
        else:
            for j in range(pageNumber):
                try:
                    tag = result['results'][j]['current_phoneres']['phoneprocessinfo']['restag']
                    if (tag == 'A') | (tag == 'B') | (tag == 'C') | (tag == 'D'):
                        addData(result, j)
                        downloads(result, j, downloadsCount)
                except:
                    print(result['results'][j])
                    print('tag error')
                    continue

if __name__ == '__main__':
    email = "test"
    password = "test"
    login(email, password)
    downloadsCount = 0
    totalPageNumber = 300
    pageNumber = 300
    fileName = 'download'
    # 判断文件夹不存在就创建文件夹
    if not os.path.exists(fileName):
        os.mkdir(fileName)
    # 将脚本的工作环境移动到创建的文件夹下
    os.chdir(fileName)
    downloadsServer(downloadsCount , pageNumber, totalPageNumber)
    db.close()
    cur.close()
    print('downloads mp3 number : ' + str(downloadsCount))
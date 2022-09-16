import requests
import logging
import base64
import time
import os
import ddddocr
from bs4 import BeautifulSoup
from Crypto.Cipher import PKCS1_v1_5 as PKCS
from Crypto.PublicKey import RSA

# 设置debug等级
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s')
ocr = ddddocr.DdddOcr(show_ad=False)

USERNAME = os.environ.get('USERNAME','')
PASSWORD = os.environ.get('PASSWORD','')
RETRY    = int(os.environ.get('RETRY',3))

pubkey = '-----BEGIN PUBLIC KEY-----\n'
pubkey += 'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQD5uIDebA2qU746e/NVPiQSBA0Q'
pubkey += '3J8/G23zfrwMz4qoip1vuKaVZykuMtsAkCJFZhEcmuaOVl8nAor7cz/KZe8ZCNIn'
pubkey += 'bXp2kUQNjJiOPwEhkGiVvxvU5V5vCK4mzGZhhawF5cI/pw2GJDSKbXK05YHXVtOA'
pubkey += 'mg17zB1iJf+ie28TbwIDAQAB'
pubkey += '\n-----END PUBLIC KEY-----'

def encrpt(input):
    rsakey = RSA.importKey(pubkey)
    cipher = PKCS.new(rsakey)
    cipher_text = base64.b64encode(cipher.encrypt(input.encode()))
    return cipher_text.decode()

headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'}

def login(session):
    code_list = []
    logging.info('decoding verify-code...')
    for i in range(0,5):
        time.sleep(2)
        response = session.get(url="https://www.bjyouth.net",headers=headers)

        document = BeautifulSoup(response.text,features="lxml")
        csrf = document.select('input[name="_csrf"]')[0].attrs.get('value')
        code_url = 'https://www.bjyouth.net' + document.select('#login-verifycode-image')[0].attrs.get('src')

        img_data = session.get(url=code_url,headers=headers).content
        # with open('./code.png','wb')as fp:
        #     fp.write(img_data)

        code = ocr.classification(img_data).replace('l','1')

        if len(code) < 4:
            continue

        found = False
        for i in code_list:
            if i['code'] == code:
                i['credence'] += 1
                found = True
                break
        if(found == False):
            code_list.append({'code':code,'credence':1})

    code_list.sort(key = lambda x:x['credence'],reverse=True)
    logging.info('decoding result: %s',code_list)
    code = code_list[0]['code']

    data = {
        '_csrf':csrf,
        'Login[username]':encrpt(USERNAME),
        'Login[password]':encrpt(PASSWORD),
        'Login[verifyCode]':code,
        'Login[smsCode]':''    
    }

    session.post(url='https://www.bjyouth.net/site/need-code',headers=headers,data=data)
    response = session.post(url='https://www.bjyouth.net/site/loginnn',headers=headers,data=data)

    if response.text.find('url') >= 0:
        logging.info('login success')
        return True
    logging.info('login failed. response: %s',response.text)
    return False
    

def get_data(session):
    response = session.get(url="https://www.bjyouth.net/statistics/dxx-league",headers=headers)

    document = BeautifulSoup(response.text,features="lxml")
    tbody = document.select('tbody > tr')
    todo = []
    for tr in tbody:
        todo.append(tr.select('td')[1].string)
    return todo


if __name__ == '__main__':
    times = 1
    logging.info('retry times limit: %d',RETRY)
    while times <= RETRY:
        times += 1
        session = requests.Session()
        try:
            if login(session):
                todo = '{}'.format(get_data(session))
                logging.info('todo list: %s',todo)
                exit()
            elif times < RETRY:
                logging.info('retrying... times: %d',times)
        except Exception as e:
            pass
        time.sleep(5)
    logging.info('failed to check data')
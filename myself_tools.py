import json
import os
import random
import string
import threading
import time

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import psutil
import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
}

requests_RequestException = requests.exceptions.RequestException
requests_ConnectionError = requests.ConnectionError
requests_ChunkedEncodingError = requests.exceptions.ChunkedEncodingError
digit_english = string.ascii_lowercase + string.digits


def badname(name):
    ban = r'\/:*?"<>|.'
    """
    避免不正當名字出現導致資料夾或檔案無法創建。
    """
    for i in ban:
        name = str(name).replace(i, ' ')
    return name.strip()


def basic_config():
    """
    每次打開會判斷有沒有 config.json。
    """
    config = {'path': os.getcwd(), 'speed': {'type': 'slow', 'value': 1}, 'simultaneous': 5,
              'status_bar': True, 'update': True}
    if not os.path.isfile('config.json'):
        data = config
        json.dump(data, open('config.json', 'w', encoding='utf-8'), indent=2)
    else:
        data = json.load(open('config.json', 'r', encoding='utf-8'))
        for k, v in config.items():
            if k not in data:
                data[k] = v
        json.dump(data, open('config.json', 'w', encoding='utf-8'), indent=2)
    download_queue = list()
    load_download_end_anime = list()
    if not os.path.isdir('Log'):
        os.mkdir('Log')
    if not os.path.isdir('./Log/undone'):
        os.mkdir('./Log/undone')
    if not os.path.isdir('./Log/history'):
        os.mkdir('./Log/history')
    for json_name in os.listdir('./Log/undone'):
        file = json.load(open(f'./Log/undone/{json_name}', 'r', encoding='utf-8'))
        if file['schedule'] == 100:
            load_download_end_anime.append(file['total_name'])
    if os.path.isfile('./Log/DownloadQueue.json'):
        download_queue += json.load(open('./Log/DownloadQueue.json', 'r', encoding='utf-8'))['queue']
    return data['path'], data['simultaneous'], data['speed']['value'], data['status_bar'], data[
        'update'], download_queue, load_download_end_anime

    # return data['path'], data['simultaneous'], data['speed']['value'], data['re_download']['status'], \
    #        data['re_download']['min'], data['status_bar'], data['update'], download_queue, load_download_end_anime


def load_localhost_end_anime_data():
    result = {
        'data_dict': dict(),
        'data_list': list()
    }
    if os.path.isdir('./EndAnimeData/') and os.path.isfile('./EndAnimeData/EndAnimeData.json') and \
            os.path.isdir('./EndAnimeData/preview') and os.path.isfile('./EndAnimeData/UpdateDate.json'):
        data_dict = json.load(open('./EndAnimeData/EndAnimeData.json', 'r', encoding='utf-8'))
        data_list = list(data_dict.keys())
        date = json.load(open('./EndAnimeData/UpdateDate.json', 'r', encoding='utf-8'))['Date']
        result.update({
            'data_dict': data_dict,
            'data_list': data_list,
            'date': date
        })
        return result, True
    return result, False


def get_weekly_update():
    """
    爬首頁的每周更新表。
    :return: Dict。
    """
    while True:
        try:
            res = requests.get(url='https://myself-bbs.com/portal.php', headers=headers, timeout=(5, 5))
            html = BeautifulSoup(res.text, features='lxml')
            week_dict = dict()
            for i in html.find_all('div', id='tabSuCvYn'):
                for index, j in enumerate(i.find_all('div', class_='module cl xl xl1')):
                    num = j.find_all('a') + j.find_all('span')
                    color = list()
                    anime_data = dict()
                    for k, v in enumerate(j.find_all('font')):
                        if k % 3 == 2:
                            color.append(v.attrs['style'])
                    for k in range(len(num) // 2):
                        anime_data.update({num[k]['title']: {'update': num[k + len(num) // 2].text, 'color': color[k],
                                                             'url': f'https://myself-bbs.com/{num[k]["href"]}'}})
                    week_dict.update({index: anime_data})
            res.close()
            res, html = None, None
            del res, html
            return week_dict
        except Exception as e:
            print(f'error get_end_anime_list: {e}')
            time.sleep(5)


def get_end_anime_list():
    """
    爬完結列表頁面的動漫資訊
    :return: Dict。
    """
    while True:
        try:
            url = 'https://myself-bbs.com/portal.php?mod=topic&topicid=8'
            res = requests.get(url=url, headers=headers, timeout=(5, 5))
            html = BeautifulSoup(res.text, features='lxml')
            data = dict()
            for index, i in enumerate(html.find_all('div', {'class': 'tab-title title column cl'})):
                month = dict()
                for j, m in enumerate(i.find_all('div', {'class': 'block move-span'})):
                    anime = dict()
                    for k in m.find('span', {'class': 'titletext'}):
                        year = k
                    for k in m.find_all('a'):
                        anime.update({k['title']: f"https://myself-bbs.com/{k['href']}"})
                    month.update({year: anime})
                data.update({index: month})
            res.close()
            return data
        except Exception as e:
            print(f'error get_end_anime_list: {e}')
            time.sleep(5)


def get_anime_data(anime_url):
    """
    爬指定動漫頁面的資料
    :param anime_url: 給網址。
    :return: Dict。
    """
    while True:
        try:
            print(anime_url)
            res = requests.get(url=anime_url, headers=headers, timeout=(5, 5))
            html = BeautifulSoup(res.text, features='lxml')
            data = {'home': anime_url, 'name': badname(html.find('title').text.split('【')[0])}
            permission = html.find('div', id='messagetext')
            if permission:
                data.update({'permission': permission.text.strip()})
            total = dict()
            for i in html.select('ul.main_list'):
                for j in i.find_all('a', href='javascript:;'):
                    title = j.text
                    for k in j.parent.select("ul.display_none li"):
                        a = k.select_one("a[data-href*='v.myself-bbs.com']")
                        if k.select_one("a").text == '站內':
                            url = a["data-href"].replace('player/play', 'vpx').replace("\r", "").replace("\n", "")
                            total.update({title: url})
            data.update({'total': total})
            for i in html.find_all('div', class_='info_info'):
                for j, m in enumerate(i.find_all('li')):
                    text = m.text
                    if j == 4:
                        text = text.split('官方網站: ')[1]
                    data.update({j: text})
            for i in html.find_all('div', class_='info_introduction'):
                for j in i.find_all('p'):
                    data.update({'info': j.text})
            for i in html.find_all('div', class_='info_img_box fl'):
                for j in i.find_all('img'):
                    while True:
                        try:
                            image = requests.get(url=j['src'], headers=headers, timeout=(5, 5)).content
                            data.update({'image': image})
                            del image
                            break
                        except Exception as e:
                            print(f'error get_anime_data image: {e}')
                        time.sleep(5)
            res.close()
            del res, html
            return data
        except requests.exceptions.ProxyError as e:
            print(f'error ProxyError get_anime_data: {e}')
            time.sleep(5)
        except Exception as e:
            print(f'error Exception get_anime_data: {e}')
            return False


def cpu_memory(info):
    """
    檢查 CPU 與 記憶體用的。
    :param info: 給 psutil.Process(pid)。
    :return:
    """
    cpu = '%.2f' % (info.cpu_percent() / psutil.cpu_count())
    memory = '%.2f' % (info.memory_full_info().rss / 1024 / 1024)
    # memory = '%.2f' % (psutil.virtual_memory().percent)
    # memory = '%.2f' % (self.info.memory_full_info().uss / 1024 / 1024)
    return {'cpu': cpu, 'memory': memory}


def kill_pid(pid):
    """
    因開了 Thread 的關係，按右上角 X 關閉時，無法將整個程式完整關掉，所以這裡下命令直接 kill，
    :param pid: 程式 pid。
    :return:
    """
    parent = psutil.Process(pid)
    for child in parent.children(recursive=True):  # or parent.children() for recursive=False
        child.kill()
    parent.kill()


def download_request(url=None, stream=False, timeout=None):
    """
    給 QT Thread 下載動漫用的。
    :param url:
    :param stream:
    :param timeout:
    :return:
    """
    return requests.get(url=url, headers=headers, stream=stream, timeout=timeout)


def get_total_page(get_html=False):
    """
    爬完結動漫總頁數多少。
    :param get_html: True = 將 requests.text 返回。
    :return: Dict。
    """
    while True:
        try:
            res = requests.get(url='https://myself-bbs.com/forum-113-1.html', headers=headers, timeout=(5, 5)).text
            html = BeautifulSoup(res, 'lxml')
            for i in html.find_all('div', class_='pg'):
                total_page = int(i.find('span')['title'].split(' ')[1])
                if get_html:
                    return {'total_page': total_page, 'html': res}
                return {'total_page': total_page}
        except Exception as e:
            print(f'error get_total_page: {e}')
            time.sleep(5)


def download_end_anime_preview(img_url):
    """
    下載圖片預覽圖用的。
    :param img_url: 給圖片URL。
    """
    return requests.get(url=img_url, headers=headers, stream=True)


def get_now_page_anime_data(page, res=None):
    """
    完結動漫頁面的動漫資料。
    :param page:要爬第幾頁。
    :param res:給完結動漫某頁的HTML，就不用requests了
    :return: Dict。
    """
    url = f'https://myself-bbs.com/forum-113-{page}.html'
    if not res:
        while True:
            try:
                res = requests.get(url=url, headers=headers, timeout=(5, 5)).text
                break
            except Exception as e:
                print(f'error get_now_page_anime_data: {e}')
                time.sleep(5)
    html = BeautifulSoup(res, 'lxml')
    data = dict()
    for i in html.find_all('div', class_='c cl'):
        anime_url = f"https://myself-bbs.com/{i.find('a')['href']}"
        anime_name = badname(i.find('a')['title'])
        anime_img = f"https://myself-bbs.com/{i.find('a').find('img')['src']}"
        anime_total_episodes = i.find('p', class_='ep_info').text
        data.update({anime_name: {'url': anime_url, 'img': anime_img, 'total': anime_total_episodes}})
    return data


def check_version(version):
    """
    檢查主程式版本用的
    :param version: 主程式目前版本
    :return: True = 有新版本，False = 最新版本。
    """
    while True:
        try:
            res = requests.get(url='https://github.com/hgalytoby/MyselfAnimeDownloader', headers=headers,
                               timeout=(5, 5)).text
            new_version = res.split('版本ver ')[1].split('<')[0]
            if new_version != version:
                return True
            return False
        except:
            time.sleep(5)


def get_login_select():
    default = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36',
    }
    while True:
        try:
            res = requests.get(url='https://myself-bbs.com/member.php?mod=logging&action=login', headers=default,
                               timeout=(5, 5))
            html = BeautifulSoup(res.text, 'lxml')
            data = {'login': {}, 'question': {}}
            for i, m in enumerate(html.find_all('select')):
                if i == 0:
                    for j in m.find_all('option'):
                        data['login'].update({j.text: j['value']})
                else:
                    for j in m.find_all('option'):
                        data['question'].update({j.text: j['value']})
            return data
        except Exception as e:
            print(f'error get_login_select: {e}')
            time.sleep(5)


def get_formhash(res_text):
    html = BeautifulSoup(res_text.text, 'lxml')
    for i in html.find_all('input', type='hidden'):
        if i['name'] == 'formhash':
            return i['value']


def myself_logout():
    if headers.get('cookie'):
        del headers['cookie']


def myself_login(login_data):
    home_url = 'https://myself-bbs.com/portal.php'
    login_url = 'https://myself-bbs.com/member.php?mod=logging&action=login&loginsubmit=yes&handlekey=login&loginhash=Lz0RU&inajax=1'
    myself_logout()
    data = {
        'referer': home_url,
        'loginfield': login_data['loginfield'],
        'username': login_data['username'],
        'password': login_data['password'],
        'questionid': login_data['questionid'],
        'answer': login_data['answer'],
        'cookietime': 2592000,
    }
    while True:
        try:
            res = requests.Session()
            home_html = res.get(url=home_url, headers=headers, timeout=(5, 5))
            data.update({'formhash': get_formhash(res_text=home_html)})
            res.post(url=login_url, headers=headers, data=data)
            if not res.cookies.get('UETw_aa10_saltkey') or not res.cookies.get('UETw_aa10_auth'):
                return False
            headers.update({
                'cookie': f'UETw_aa10_saltkey={res.cookies["UETw_aa10_saltkey"]}; UETw_aa10_auth={res.cookies["UETw_aa10_auth"]};'})
            return True
        except Exception as e:
            print(f'error myself_login: {e}')
            time.sleep(5)


def get_all_page(data):
    all_page, _ = divmod(len(data), 8)
    if _ != 0:
        all_page += 1
    return all_page


def connect_myself_anime():
    count = 0
    while count < 10:
        try:
            res = requests.get(url='https://myself-bbs.com/portal.php', headers=headers, timeout=(5, 5))
            if res.ok:
                return True
        except Exception as e:
            print(f'connect_myself_anime: {e}')
            count += 1
            time.sleep(5)
    return False


def record():
    def _():
        try:
            requests.get(url='https://myself.duduru.website/', headers=headers)
        except:
            ...

    threading.Thread(target=_).start()


def search_animate(name: str = None, url: str = None):
    data = {
        'total': 1,
        'page': 1
    }
    count = 0
    while count < 2:
        try:
            if url:
                res = requests.get(url=url, headers=headers, timeout=(5, 5))
                data['page'] = int(url.split('page=')[-1])
            else:
                res = requests.post(
                    url=f'https://myself-bbs.com/search.php?mod=forum',
                    headers=headers,
                    data={
                        'formhash': ''.join(random.sample(digit_english, 8)),
                        'srchtxt': name,
                        'searchsubmit': 'yes'
                    },
                    timeout=(5, 5)
                )
            if res.ok:
                html = BeautifulSoup(res.text, 'lxml')
                data['animate'] = [{
                    'url': f'https://myself-bbs.com/{item.find("a")["href"]}',
                    'name': item.find('a').text
                } for item in html.find_all('h3', class_='xs3')]
                if html.find('div', class_='pgs cl mbm'):
                    total_page = int(html.find('div', class_='pgs cl mbm').find('label').find('span')
                                     .attrs['title'].split('共 ')[1].split('頁')[0])
                    url = f'https://myself-bbs.com/{html.find("div", class_="pg").find("a")["href"]}'
                    data['base_url'] = f'{url.split("page=")[0]}replace_page'
                    data['total'] = total_page
                return data
            else:
                print(f'search_animate res error: {res.status_code}')
                return data
        except Exception as e:
            print(f'error search_animate: {e}')
            time.sleep(5)
            count += 1
    return data

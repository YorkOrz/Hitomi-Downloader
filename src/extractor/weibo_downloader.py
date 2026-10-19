#coding:utf8
import downloader
import ree as re
from utils import Downloader, Session, get_print, clean_title, Soup, fix_protocol, domain, get_max_range, get_ext, File, check_alive, limits
from translator import tr_
import clf2
import errors
import utils
import dateutil.parser
import time
import datetime


def suitable(url):
    if domain(url.lower(), 2) not in ['weibo.com', 'weibo.cn']:
        return False
    if '/tv/' in url.lower():
        return False
    return True


class LoginRequired(errors.LoginRequired):
    def __init__(self, *args):
        super().__init__(*args, method='browser', url='https://weibo.com/login.php', w=1180)


def read_json_api(url, referer=None, session=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'X-Requested-With': 'XMLHttpRequest',
    }
    if referer:
        headers['Referer'] = referer

    if session is not None and hasattr(session, 'get'):
        res = session.get(url, headers=headers, timeout=15)
        if hasattr(res, 'raise_for_status'):
            res.raise_for_status()
        if hasattr(res, 'json'):
            return res.json()
        import json
        return json.loads(res.text)

    return downloader.read_json(url, referer=referer, headers=headers, methods=['requests'])


class Downloader_weibo(Downloader):
    type = 'weibo'
    URLS = [suitable]
    MAX_PARALLEL = 2 #6739
    ACCEPT_COOKIES = [r'(.*\.)?(weibo\.com|sina\.com\.cn|weibo\.cn)']

    def init(self):
        self.session = Session()

    @classmethod
    def fix_url(cls, url):
        url = url.replace('weibo.cn', 'weibo.com').split('?')[0]
        if 'weibo.com/p/' in url:
            id = re.find(r'weibo.com/p/([^/]+)', url, err='no id')
            url = f'https://weibo.com/p/{id}'
        elif 'weibo.com/u/' in url:
            id = re.find(r'weibo.com/u/([^/]+)', url, err='no id')
            url = f'https://weibo.com/u/{id}'
        elif 'weibo.com/' in url:
            id = re.find(r'weibo.com/([^/]+)', url, err='no id')
            url = f'https://weibo.com/{id}'
        else:
            id = url
            url = f'https://weibo.com/u/{id}'
        return fix_protocol(url)

    def read(self):
        if hasattr(self.session, 'init'):
            try:
                self.session.init(self.cw)
            except Exception:
                pass
        ensure_cookies(self.session, self.cw)

        uid, oid, name = get_id(self.url, self.session, self.cw)
        title = clean_title(f'{name} (weibo_{uid})')

        self.urls += get_imgs(uid, title, self.session, cw=self.cw)

        self.title = title


def checkLogin(session):
    c = None
    try:
        c = session.cookies._cookies.get('.weibo.com', {}).get('/', {}).get('SUBP')
    except Exception:
        pass
    if not c or c.is_expired():
        ensure_cookies(session)


def ensure_cookies(session, cw=None):
    print_ = get_print(cw)
    try:
        sub = session.cookies.get('SUB')
        subp = session.cookies.get('SUBP')
        if sub and subp:
            return
    except Exception:
        pass

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Referer': 'https://passport.weibo.com/'
        }
        data = {
            'cb': 'gen_visitor',
            'fp': '{"os":"1","browser":"Chrome131,0,0,0","fonts":"undefined","screenInfo":"1920*1080*24","plugins":""}'
        }
        res1 = session.post('https://passport.weibo.com/visitor/genvisitor', data=data, headers=headers, timeout=15)
        m = re.find(r'"tid"\s*:\s*"([^"]+)"', res1.text)
        if not m:
            print_(f'weibo: genvisitor missing tid: {res1.text[:100]}')
            return
        tid = m if isinstance(m, str) else m[0]

        incarnate_url = f'https://passport.weibo.com/visitor/visitor?a=incarnate&t={tid}&w=2&c=095&gc=&cb=cross_domain&from=weibo&_rand={time.time()}'
        res2 = session.get(incarnate_url, headers=headers, timeout=15)
        m_sub = re.find(r'"sub"\s*:\s*"([^"]+)"', res2.text)
        m_subp = re.find(r'"subp"\s*:\s*"([^"]+)"', res2.text)
        if m_sub and m_subp:
            v_sub = m_sub if isinstance(m_sub, str) else m_sub[0]
            v_subp = m_subp if isinstance(m_subp, str) else m_subp[0]
            session.cookies.set('SUB', v_sub, domain='.weibo.com', path='/')
            session.cookies.set('SUBP', v_subp, domain='.weibo.com', path='/')
            session.cookies.set('SUB', v_sub, domain='weibo.com', path='/')
            session.cookies.set('SUBP', v_subp, domain='weibo.com', path='/')
        print_('weibo: visitor cookies acquired')
    except Exception as e:
        print_(f'weibo: ensure_cookies error: {e}')


class Album:

    def __init__(self, id, type):
        self.id = id
        self.type = type


@limits(1)
def wait():
    pass


class Image(File):

    type = 'weibo'
    format = '[date] id_ppage'


def _get_page_id(html):
    return re.find(r"CONFIG\['page_id'\]='([0-9]+)'", html) or re.find(r'/u/page/follow/([0-9]+)', html)


def get_id(url, session=None, cw=None):
    if session is not None and not hasattr(session, 'cookies'):
        cw = session
        session = None
    if session is None:
        session = Session()
        ensure_cookies(session, cw)

    print_ = get_print(cw)
    url_clean = url.split('?')[0].rstrip('/')

    kind = None
    val = None

    if '/u/' in url_clean:
        kind = 'uid'
        val = url_clean.split('/u/')[-1].split('/')[0]
    elif '/p/' in url_clean:
        p_val = url_clean.split('/p/')[-1].split('/')[0]
        if p_val.startswith('100505') and len(p_val) > 6:
            kind = 'uid'
            val = p_val[6:]
        else:
            kind = 'custom'
            val = p_val
    elif '/n/' in url_clean:
        kind = 'custom'
        val = url_clean.split('/n/')[-1].split('/')[0]
    elif 'weibo.com/' in url_clean:
        part = url_clean.split('weibo.com/')[-1].split('/')[0]
        if part.isdigit():
            kind = 'uid'
            val = part
        elif part:
            kind = 'custom'
            val = part
    else:
        part = url_clean.strip('/')
        if part.isdigit():
            kind = 'uid'
            val = part
        else:
            kind = 'custom'
            val = part

    if not val:
        raise errors.Invalid(f'Invalid Weibo URL: {url}')

    if kind == 'uid':
        api_url = f'https://weibo.com/ajax/profile/info?uid={val}'
    else:
        api_url = f'https://weibo.com/ajax/profile/info?custom={val}'

    try:
        d = read_json_api(api_url, referer=url, session=session)
    except Exception as e:
        print_(f'weibo: read_json error for profile info: {e}')
        if kind == 'uid':
            return val, None, f'user_{val}'
        raise errors.Invalid(f'Weibo user not found: {url}')

    data = d.get('data', {}) if isinstance(d, dict) else {}
    user = data.get('user', {})
    if not user:
        if isinstance(d, dict) and d.get('ok') == 0:
            msg = d.get('msg', 'User not found or access denied')
            if 'login' in msg.lower() or '登录' in msg:
                raise LoginRequired(msg)
            raise errors.Invalid(f'Weibo user not found: {msg}')
        if kind == 'uid':
            return val, None, f'user_{val}'
        raise errors.Invalid(f'Could not find Weibo user for {url}')

    uid = str(user.get('id') or val)
    name = user.get('screen_name') or user.get('name') or uid
    return uid, None, name


def extract_video(d):
    return d.get('stream_url_hd') or d.get('stream_url')


def get_imgs(uid, title, session, cw=None): #6739
    print_ = get_print(cw)
    print_(f'uid: {uid}')

    olds = utils.process_olds(Image, title, r'([0-9]+)_p', cw)
    mids = olds['ids']
    imgs_old = olds['imgs']

    referer = f'https://weibo.com/u/{uid}?tabtype=album'
    imgs = []
    sinceid = None

    while check_alive(cw):
        if sinceid:
            url_api = f'https://weibo.com/ajax/profile/getImageWall?uid={uid}&sinceid={sinceid}'
        else:
            url_api = f'https://weibo.com/ajax/profile/getImageWall?uid={uid}&sinceid=0&has_album=true'
        wait()
        try:
            d = read_json_api(url_api, referer=referer, session=session)
        except Exception as e:
            print_(f'weibo: getImageWall error: {e}')
            break

        if not d or not isinstance(d, dict) or 'data' not in d:
            break
        sinceid = d['data'].get('since_id')
        items = d['data'].get('list', [])
        if not items:
            break

        for item in items:
            mid = int(item['mid'])
            if mid in mids:
                continue
            mids.add(mid)
            url_api = f'https://weibo.com/ajax/statuses/show?id={mid}'
            wait()
            d_status = None
            try:
                d_status = read_json_api(url_api, referer=referer, session=session)
            except Exception as e:
                print_(f'statuses/show failed for {mid}: {e}')

            media_info = []
            date = None
            if d_status and isinstance(d_status, dict) and d_status.get('ok') == 1:
                try:
                    date = dateutil.parser.parse(d_status['created_at'])
                except Exception:
                    pass
                structs = [d_status] + (d_status.get('url_struct') or [])
                for struct in structs:
                    media_info = struct.get('mix_media_info', {}).get('items') or (list(struct.get('pic_infos', {}).values()) if struct.get('pic_infos') else None)
                    if media_info:
                        break

                if not media_info and d_status.get('page_info', {}).get('media_info'):
                    media_info = [{'type': 'video', 'data': {'media_info': d_status['page_info']['media_info']}}]

                if not media_info and d_status.get('retweeted_status'):
                    retweet = d_status['retweeted_status']
                    structs_rt = [retweet] + (retweet.get('url_struct') or [])
                    for struct in structs_rt:
                        media_info = struct.get('mix_media_info', {}).get('items') or (list(struct.get('pic_infos', {}).values()) if struct.get('pic_infos') else None)
                        if media_info:
                            break
                    if not media_info and retweet.get('page_info', {}).get('media_info'):
                        media_info = [{'type': 'video', 'data': {'media_info': retweet['page_info']['media_info']}}]

            if media_info:
                for p, m_item in enumerate(media_info):
                    data = m_item.get('data')
                    if data:
                        m_type = m_item.get('type')
                        if m_type == 'video':
                            img_url = extract_video(data.get('media_info', {}))
                        elif m_type == 'pic':
                            img_url = data.get('largest', {}).get('url')
                        else:
                            continue
                    else:
                        img_url = m_item.get('largest', {}).get('url')

                    if not img_url:
                        continue

                    ext = get_ext(img_url)
                    d_fmt = {
                        'date': date or datetime.datetime.now(),
                        'id': mid,
                        'page': p,
                    }
                    filename = utils.format('weibo', d_fmt, ext)
                    imgs.append(Image({'referer': referer, 'url': img_url, 'name': filename}))
            elif item.get('pid'):
                pid = item['pid']
                img_url = f'https://wx1.sinaimg.cn/large/{pid}.jpg'
                ext = '.jpg'
                if date is None:
                    try:
                        y = int(item.get('timeline_year', 2026))
                        m = int(item.get('timeline_month', 1))
                        date = datetime.datetime(y, m, 1)
                    except Exception:
                        date = datetime.datetime.now()
                d_fmt = {
                    'date': date,
                    'id': mid,
                    'page': 0,
                }
                filename = utils.format('weibo', d_fmt, ext)
                imgs.append(Image({'referer': referer, 'url': img_url, 'name': filename}))
            else:
                print_(f'no media: {mid}')
                continue

            cw.setTitle(f'{tr_("읽는 중...")}  {title} - {len(imgs)}')

        if not sinceid:
            break

        if len(imgs) >= get_max_range(cw):
            break

    return imgs + imgs_old

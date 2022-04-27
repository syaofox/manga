import asyncio
import urllib
import os
import math
import re
from mods.datamgr import Comic
from mods.logouter import Logouter
from mods.utils import md5, extrat_extname
from mods.zipper import Zipper
from PIL import Image
from parsers.parserex import ParserEx
from playwright.async_api import Page, BrowserContext
from pyquery import PyQuery as pq


class Comic18exParser(ParserEx):

    def __init__(self) -> None:
        self.semaphore_down = asyncio.Semaphore(10)

    @property
    def name(self):
        return 'comic18ex'

    @staticmethod
    def get_rows(aid, img_url):
        '''
        获取分割数量的函数
        '''
        #220980
        #268850
        pattern = '/([0-9]*)\.jpg'
        l = re.findall(pattern, img_url)[0]
        num = 0
        if aid < 220980:
            num = 0
        elif aid < 268850:
            num = 10
        else:
            num_str = str(aid) + l
            # num_str = num_str.encode()
            # num_str = hashlib.md5(num_str).hexdigest()
            num_str = md5(num_str)
            num = ord(num_str[-1])
            num %= 10
            num = num * 2 + 2
        return num

    @staticmethod
    def fix_jpg20(img_url, num=0):
        """
        该函数对某个文件夹下的图片进行解密并在指定文件夹存储
        """
        if num == 0:
            return img_url
        source_img = Image.open(img_url)
        w, h = source_img.size
        decode_img = Image.new("RGB", (w, h))
        remainder = h % num
        copyW = w
        try:
            for i in range(num):
                copyH = math.floor(h / num)
                py = copyH * i
                y = h - (copyH * (i + 1)) - remainder
                if i == 0:
                    copyH = copyH + remainder
                else:
                    py = py + remainder
                temp_img = source_img.crop((0, y, copyW, y + copyH))
                decode_img.paste(temp_img, (0, py, copyW, py + copyH))
            decode_img.save(img_url)
            return True
        except Exception:
            return False

    async def click_popup(self, page: Page):
        btn1 = await page.query_selector('text=我保證我已满18歲！')
        if btn1 and await btn1.is_visible():
            await page.locator('text=我保證我已满18歲！').click()

        btn2 = await page.query_selector('text=確定進入！')
        if btn2 and await btn2.is_visible():
            await page.locator('text=確定進入！').click()

    def getch_comic_info(self, doc):
        name = doc('div.panel-heading').eq(0).text().strip('\n')
        if name is None:
            raise Exception('获取漫画名字失败')

        author = [a.text() for a in doc('div:contains("作者")>span[itemprop="author"]').items()][0]

        intro = doc('div.p-t-5:contains("敘述：")').text()
        cover_url = doc('#album_photo_cover img[itemprop*="image"]').attr('src')
        return name, author, intro, cover_url

    async def parse_main_page(self, browser: BrowserContext, page: Page, url, param=None):
        await super().parse_main_page(browser, page, url, param)
        self.click_popup(page=page)

    async def fetch_chapters(self, page, doc):

        episodes = doc('div.episode').eq(0)
        els = episodes('ul.btn-toolbar>a')
        for el in els.items():

            url = urllib.parse.urljoin(page.url, el.attr('href'))
            title = el('li').text().strip('\n').replace('最新 ', '')
            keystr = md5(url)
            if not Comic.chapters.get(keystr, None):
                Comic.chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        if len(els) <= 0:
            surl = doc('a.reading').attr('href')
            url = urllib.parse.urljoin(page.url, surl.strip('\n'))
            title = '全一卷'
            keystr = md5(url)
            if not Comic.chapters.get(keystr, None):
                Comic.chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

    async def parse_chapter_page(self, browser: BrowserContext, page: Page, url, param=None):
        await self.click_popup(page)
        return await super().parse_chapter_page(browser, page, url, param)

    def down_done(self, fname, data):
        fixparam = data.get('fixparam', None)
        if fixparam and fixparam > 0:
            self.fix_jpg20(fname, fixparam)

    async def fetch_pices(self, browser, url, chapter_dir, doc, html):

        ## 解密参数
        is_need_fix = False
        ids = re.search(r'<script>.*?var.*?scramble_id.*?=.*?(\d+);.*?var.*?aid.*?=.*?(\d+);', html, re.S)
        aid = 0
        if ids:
            scramble_id = int(ids.group(1))
            aid = int(ids.group(2))
            is_need_fix = (aid >= scramble_id)

        els = doc('div.panel-body>div.row.thumb-overlay-albums>div>img')
        pices_total_num = len(els)
        Logouter.pic_total += pices_total_num
        Logouter.crawlog()

        down_tasks = []

        for i, el in enumerate(els.items()):
            purl = el.attr('data-original').strip()
            pic_fname = os.path.join(chapter_dir, f'{str(i).zfill(4)}.{extrat_extname(purl)}')

            fixparm = 0
            if 'media/photos' in purl and is_need_fix:  # 对非漫画图片连接直接放行
                fixparm = self.get_rows(aid, purl)

            pic = {'url': purl, 'fname': pic_fname, 'fixparam': fixparm}

            down_task = asyncio.create_task(self.down(pic, browser))
            down_tasks.append(down_task)

        await asyncio.gather(*down_tasks)

        downloaded_count = Zipper.count_dir(chapter_dir)
        if downloaded_count == pices_total_num:
            Zipper.zip(chapter_dir)
            Comic.chapters[md5(url)]['status'] = 1
            Comic.save_to_json()

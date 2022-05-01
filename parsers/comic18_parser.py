import asyncio
import re
from time import time
import urllib
import lzstring
import os
import math
from pyquery import PyQuery as pq
from mods.datamgr import Comic
from mods.logouter import Logouter
from mods.utils import md5, extrat_extname, extrat_fname, valid_filename
from mods.zipper import Zipper
from parsers.parser import Parser
from playwright.async_api import Page, Response, Error, BrowserContext
from mods.picchecker import PicChecker
from PIL import Image
from io import BytesIO


class Comic18Paser(Parser):

    @property
    def name(self):
        return '18comic'

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

    @staticmethod
    def fix_jpgdata(img_data, num=0):
        """
        该函数对某个文件夹下的图片进行解密并在指定文件夹存储
        """
        if num == 0:
            return img_data
        stream = BytesIO(img_data)
        source_img = Image.open(stream).convert("RGBA")
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
            return decode_img

        except Exception:
            return False
        finally:
            stream.close()

    async def click_popup(self, page: Page):
        btn1 = await page.query_selector('text=我保證我已满18歲！')
        if await btn1.is_visible():
            await page.locator('text=我保證我已满18歲！').click()

        btn2 = await page.query_selector('text=確定進入！')
        if await btn2.is_visible():
            await page.locator('text=確定進入！').click()

    async def parse_main_page(self, browser: BrowserContext, page: Page, url, param=None):
        param['cover_imgdatas'] = {}

        async def handle_response(response: Response):

            if response.ok and (response.request.resource_type == "image"):
                await response.finished()
                imgdata = await response.body()
                # Logouter.pic_crawed += 1
                # Logouter.crawlog()

                imgdata = await response.body()
                param['cover_imgdatas'][md5(response.url)] = imgdata

        page.on("response", handle_response)
        await page.goto(url, wait_until='domcontentloaded', timeout=100000)
        await page.wait_for_load_state('networkidle')

        await self.click_popup(page)

        html = await page.content()
        doc = pq(html)

        # 基础信息
        name = doc('div.panel-heading').eq(0).text().strip('\n')
        if name is None:
            raise Exception('获取漫画名字失败')

        author = [a.text() for a in doc('div:contains("作者")>span[itemprop="author"]').items()][0]

        intro = doc('div.p-t-5:contains("敘述：")').text()
        cover_url = doc('#album_photo_cover img[itemprop*="image"]').attr('src')

        Comic.set_comic_name(name)
        Comic.set_author(author)
        Comic.main_url = page.url
        Comic.intro = intro
        Comic.save_to_json()

        if cover_url:
            keystr = md5(cover_url)
            imgdata = param['cover_imgdatas'].get(keystr, None)

            if not imgdata:
                Logouter.red(f'漏网{cover_url}')
                raise Exception(f'下载封面失败={cover_url}')

            cover_fname = os.path.join(Comic.get_full_comicdir(), f'cover.{extrat_extname(cover_url)}')

            with open(cover_fname, 'wb') as f:
                f.write(imgdata)

            if not PicChecker.valid_pic(cover_fname):
                os.remove(cover_fname)
                Logouter.pic_failed += 1
                Logouter.crawlog()
                raise Exception(f'下载失败！下载图片不完整={cover_fname}')

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

        Logouter.chapter_total = len(Comic.chapters)
        Logouter.crawlog()
        Comic.save_to_json()

    async def parse_chapter_page(self, browser: BrowserContext, page: Page, url, param=None):

        param['chapter_url'] = url
        categories_str = valid_filename(f'{param["categories"]}')
        chapter_str = valid_filename(f'{param["chapter"]}')
        chapter_dir = os.path.join(Comic.get_full_comicdir(), categories_str, chapter_str)

        param['chapter_dir'] = chapter_dir
        if not os.path.exists(chapter_dir):
            os.makedirs(chapter_dir)

        param['pices_count'] = 0
        param['pices_datas'] = {}

        param['busy'] = True

        async def handle_response(response: Response):

            if response.ok:
                if (response.request.resource_type == "image"):
                    await response.finished()
                    # 保存页面上的图像数据
                    imgdata = await response.body()
                    param['pices_datas'][md5(response.url)] = imgdata

        # 首次访问获得图片地址
        page.on("response", handle_response)
        await page.goto(url, wait_until='networkidle', timeout=100000)

        await self.click_popup(page)

        await page.keyboard.press("Home")
        await page.wait_for_load_state('networkidle')

        await page.wait_for_load_state('networkidle')

        els = await page.query_selector_all('div.panel-body>div.row.thumb-overlay-albums>div>img')

        param['pices_count'] = len(els)
        Logouter.pic_total += param['pices_count']
        Logouter.crawlog()

        html = await page.content()
        is_need_fix = False
        ids = re.search(r'<script>.*?var.*?scramble_id.*?=.*?(\d+);.*?var.*?aid.*?=.*?(\d+);', html, re.S)
        aid = 0
        if ids:
            scramble_id = int(ids.group(1))
            aid = int(ids.group(2))
            is_need_fix = (aid >= scramble_id)

        purls = {}

        for i, el in enumerate(els):
            purl = await el.get_attribute('data-original')
            pic_fname = os.path.join(param['chapter_dir'], f'{str(i).zfill(4)}.{extrat_extname(purl)}')
            purls[md5(purl)] = {'url': purl, 'fname': pic_fname}

        cur_pos = 1
        downloaded = 0

        # 判断是否所有图片都缓存到
        while True:
            await page.query_selector_all('div.panel-body>div.row.thumb-overlay-albums>div>img.lazy_img.img-responsive-mw.lazy-loaded')

            for urlmd5, pic_data in purls.copy().items():
                pic_fname = pic_data['fname']
                pic_url = pic_data['url']
                imgdata = param['pices_datas'].get(urlmd5, None)
                if not imgdata:
                    continue

                if os.path.exists(pic_fname):
                    if PicChecker.valid_pic(pic_fname):
                        param['pices_datas'].pop(urlmd5)
                        purls.pop(urlmd5)
                        Logouter.pic_crawed += 1
                        downloaded += 1
                        Logouter.crawlog()
                        continue
                    else:
                        os.remove(pic_fname)

                fixparm = 0

                if 'media/photos' in pic_url and is_need_fix:  # 对非漫画图片连接直接放行
                    fixparm = self.get_rows(aid, pic_url)

                file_data = imgdata
                if fixparm > 0:
                    file_data = self.fix_jpgdata(imgdata, fixparm)
                    file_data.save(pic_fname)

                else:
                    with open(pic_fname, 'wb') as f:
                        f.write(file_data)

                if not PicChecker.valid_pic(pic_fname):
                    os.remove(pic_fname)
                    Logouter.pic_failed += 1
                    Logouter.crawlog()
                    raise Exception(f'下载失败！下载图片不完整={pic_fname}')

                Logouter.pic_crawed += 1
                downloaded += 1
                Logouter.crawlog()

                param['pices_datas'].pop(urlmd5)
                purls.pop(urlmd5)

            if downloaded == param['pices_count']:
                break

            cur_pos = min(param['pices_count'], cur_pos)
            await page.locator('#pageselect').select_option(str(cur_pos))
            await page.wait_for_load_state('networkidle')
            cur_pos += 1

            if cur_pos >= param['pices_count']:
                cur_pos = 1

        await page.wait_for_load_state('networkidle')

        downloaded_count = Zipper.count_dir(param['chapter_dir'])
        if downloaded_count == param['pices_count']:

            Zipper.zip(param['chapter_dir'])
            Comic.chapters[md5(url)]['status'] = 1
            Comic.save_to_json()

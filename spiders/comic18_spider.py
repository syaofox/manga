import os
import re
import urllib
import lzstring
import math
from playwright.async_api import Response, Page
from mods.logouter import Logouter
from mods.picchecker import PicChecker
from mods.utils import extrat_extname, md5, valid_filename
from pyquery import PyQuery as pq
from mods.zipper import Zipper
from spiders.wspider import WSpider
from PIL import Image
from io import BytesIO


class Comic18Spider(WSpider):

    @property
    def name(self):
        return '18comic'

    async def fetch_comic_info_sub(self, page):
        await page.goto(self.config.comic_url, wait_until='networkidle', timeout=100000)
        await self.click_popup(page)

        html = await page.content()
        doc = pq(html)

        self.comic_name = doc('div.panel-heading').eq(0).text().strip('\n')
        if self.comic_name is None:
            raise Exception('获取漫画名字失败')
        self.author = [a.text() for a in doc('div:contains("作者")>span[itemprop="author"]').items()][0]
        self.intro = doc('div.p-t-5:contains("敘述：")').text()
        self.cover_url = doc('#album_photo_cover img[itemprop*="image"]').attr('src')

    async def fetch_chapters(self, page):
        await super().fetch_chapters(page)

        html = await page.content()
        doc = pq(html)

        episodes = doc('div.episode').eq(0)
        els = episodes('ul.btn-toolbar>a')
        for el in els.items():

            url = urllib.parse.urljoin(page.url, el.attr('href'))
            title = el('li').text().strip('\n').replace('最新 ', '')
            keystr = md5(url)
            if not self.chapters.get(keystr, None):
                self.chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        if len(els) <= 0:
            surl = doc('a.reading').attr('href')
            url = urllib.parse.urljoin(page.url, surl.strip('\n'))
            title = '全一卷'
            keystr = md5(url)
            if not self.chapters.get(keystr, None):
                self.chapters[keystr] = {'categories': '连载', 'title': title, 'url': url, 'status': 0}

        Logouter.chapter_total = len(self.chapters)
        Logouter.crawlog()

    async def click_popup(self, page: Page):
        return
        btn1 = await page.query_selector('text=我保證我已满18歲！')
        if await btn1.is_visible():
            await page.locator('text=我保證我已满18歲！').click()
            await page.wait_for_timeout(500)

        btn2 = await page.query_selector('text=確定進入！')
        if await btn2.is_visible():
            await page.locator('text=確定進入！').click()
            await page.wait_for_timeout(500)

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

    def save_imageex(self, urlmd5, pic_name, fixparam):
        if os.path.exists(pic_name):
            if PicChecker.valid_pic(pic_name):
                return True
            else:
                os.remove(pic_name)

        imgdata = self.pices_data.get(urlmd5, None)

        if not imgdata:
            return False

        file_data = imgdata
        if fixparam > 0:
            file_data = self.fix_jpgdata(imgdata, fixparam)
            file_data.save(pic_name)

        else:
            with open(pic_name, 'wb') as f:
                f.write(file_data)

        if not PicChecker.valid_pic(pic_name):
            os.remove(pic_name)
            raise Exception(f'下载失败！下载图片不完整={pic_name}')

    async def fetch_pices_sub(self, chapter, chapter_dir):

        async def handle_response(response: Response):
            if response.ok:
                if (response.request.resource_type == "image"):
                    # 保存页面上的图像数据
                    await response.finished()
                    imgdata = await response.body()
                    self.pices_data[md5(response.url)] = imgdata

        page = await self.get_page()
        page.on("response", handle_response)
        await page.goto(chapter['url'], wait_until='networkidle', timeout=100000)
        await self.click_popup(page)
        await page.keyboard.press("Home")

        els = await page.query_selector_all('div.panel-body>div.row.thumb-overlay-albums>div>img')
        page_count = len(els)
        Logouter.pic_total += page_count
        Logouter.crawlog()

        html = await page.content()

        # 读取图片加密信息
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
            pic_fname = os.path.join(chapter_dir, f'{str(i).zfill(4)}.{extrat_extname(purl)}')
            purls[md5(purl)] = {'url': purl, 'fname': pic_fname}

        cur_pos = 1
        downloaded = 0

        # 判断是否所有图片都缓存到
        while True:
            await page.query_selector_all('div.panel-body>div.row.thumb-overlay-albums>div>img.lazy_img.img-responsive-mw.lazy-loaded')

            for urlmd5, pic_data in purls.copy().items():
                pic_fname = pic_data['fname']
                pic_url = pic_data['url']

                # 获取加密参数
                fixparm = 0
                if 'media/photos' in pic_url and is_need_fix:  # 对非漫画图片连接直接放行
                    fixparm = self.get_rows(aid, pic_url)

                if self.save_imageex(urlmd5, pic_fname, fixparm):
                    Logouter.pic_crawed += 1
                    downloaded += 1
                    Logouter.crawlog()
                    if self.pices_data.get(urlmd5, None):
                        self.pices_data.pop(urlmd5)
                    purls.pop(urlmd5)

            if downloaded == page_count:
                break

            cur_pos = min(page_count, cur_pos)
            await page.locator('#pageselect').select_option(str(cur_pos))
            await page.wait_for_load_state('networkidle')
            cur_pos += 1

            if cur_pos >= page_count:
                cur_pos = 1

        await page.wait_for_load_state('networkidle')

        downloaded_count = Zipper.count_dir(chapter_dir)
        if downloaded_count == page_count:
            Zipper.zip(chapter_dir)
            self.chapters[md5(chapter['url'])]['status'] = 1
            Logouter.chapter_successed += 1
            Logouter.crawlog()
            self.save_base_info()

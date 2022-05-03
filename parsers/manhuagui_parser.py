import asyncio
import re
import urllib
import lzstring
import os

from pyquery import PyQuery as pq
from mods.datamgr import Comic
from mods.logouter import Logouter
from mods.utils import md5, extrat_extname, extrat_fname, valid_filename
from mods.zipper import Zipper
from parsers.parser import Parser
from playwright.async_api import Page, Response, Error, BrowserContext
from mods.picchecker import PicChecker


class ManhuaguiPaser(Parser):

    pices_data = {}
    cover_imgdatas = {}

    @property
    def name(self):
        return 'manhuagui'

    def getch_comic_info(self, page, doc: pq):
        """获得name,author intro cover_urk

        Args:
            doc (pq): _description_

        Returns:
            _type_: _description_
        """
        name = doc('div.book-title>h1').text()
        if name is None:
            raise Exception('获取漫画名字失败')
        author = doc('div.book-detail.pr.fr > ul> li:nth-child(2)>span:nth-child(2)> a').text()
        intro = doc('#intro-cut').text()
        cover_url = urllib.parse.urljoin(page.url, doc('p.hcover > img').attr('src'))
        return name, author, intro, cover_url

    async def parse_main_page(self, browser: BrowserContext, page: Page, url, param=None):
        self.cover_imgdatas = {}

        async def handle_response(response: Response):

            if response.ok and (response.request.resource_type == "image"):
                await response.finished()
                imgdata = await response.body()
                self.cover_imgdatas[md5(response.url)] = imgdata

        page.on("response", handle_response)
        await page.goto(url, wait_until='domcontentloaded', timeout=100000)
        await page.wait_for_load_state('networkidle')

        html = await page.content()
        doc = pq(html)

        # 基础信息
        name, author, intro, cover_url = self.getch_comic_info(page, doc)

        Comic.set_comic_name(name)
        Comic.set_author(author)
        Comic.main_url = page.url
        Comic.intro = intro
        Comic.save_to_json()

        if cover_url:
            keystr = md5(cover_url)
            imgdata = self.cover_imgdatas.get(keystr, None)

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

        await self.fetch_chapters(page, doc)

        Logouter.chapter_total = len(Comic.chapters)
        Logouter.crawlog()
        Comic.save_to_json()

    async def fetch_chapters(self, page, doc):
        """获取章节信息

        Args:
            page (Page): _description_
            url (_type_): _description_
            param (_type_, optional): _description_. Defaults to None.
            doc (_type_, optional): _description_. Defaults to None.
        """
        # 章节
        if await page.query_selector('#__VIEWSTATE'):
            lzstrings = doc('#__VIEWSTATE').attr('value')
            deslzstring = lzstring.LZString().decompressFromBase64(lzstrings)
            doc = pq(deslzstring)
            chapter_divs = doc('div.chapter-list')
            heads = [el.text() for el in doc('h4').items()]
        else:
            await page.wait_for_selector('div.chapter>div.chapter-list')
            chapter_divs = doc('div.chapter>div.chapter-list')
            heads = [el.text() for el in doc('body > div.w998.bc.cf> div.fl.w728 > div.chapter.cf.mt16 > h4').items()]

        for i, chapter_div in enumerate(chapter_divs.items()):
            els = chapter_div('li>a')
            categories = heads[i]

            for el in els.items():
                url = urllib.parse.urljoin(page.url, el.attr('href'))
                keystr = md5(url)

                chapterdata = Comic.chapters.get(keystr, None)
                if not chapterdata:
                    title = f"{el.attr('title')}({el('span>i').text()})"
                    Comic.chapters[keystr] = {'categories': categories, 'title': title, 'url': url, 'status': 0}

    def pices_rule(self, url):
        """检测需要下载哪些文件

        Args:
            url (_type_): 图片url
        """
        return not ('/images/' in url)

    async def parse_pices(self, page: Page, url, param=None):
        """抓取章节图片

        Args:
            page (Page): _description_
            url (_type_): _description_
            param (_type_, optional): _description_. Defaults to None.
        """
        await page.wait_for_selector('#mangaFile')

        html = await page.content()
        doc = pq(html)

        if await page.query_selector('#checkAdult'):
            await page.click('#checkAdult')

        count_info = doc('body > div.w980.title > div:nth-child(2) > span').text()
        idxs = re.search(r'\((\d+)/(\d+)\)', count_info)
        cur_idx = int(idxs.group(1))
        page_count = int(idxs.group(2))
        Logouter.pic_total += page_count
        Logouter.crawlog()

        while True:
            await asyncio.sleep(0.1)
            if not param['busy']:
                param['busy'] = True
                if cur_idx < page_count:
                    await page.locator('#next').click()

                    await page.wait_for_load_state("networkidle")

                    html = await page.content()
                    doc = pq(html)

                    count_info = doc('body > div.w980.title > div:nth-child(2) > span').text()
                    idxs = re.search(r'\((\d+)/(\d+)\)', count_info)
                    cur_idx = int(idxs.group(1))
                    page_count = int(idxs.group(2))

                if cur_idx >= page_count:

                    downloaded_count = Zipper.count_dir(param['chapter_dir'])
                    if downloaded_count == page_count:
                        Zipper.zip(param['chapter_dir'])
                        Comic.chapters[md5(url)]['status'] = 1
                        Comic.save_to_json()
                    break

    async def parse_chapter_page(self, browser: BrowserContext, page: Page, url, param=None):

        param['chapter_url'] = url
        categories_str = valid_filename(f'{param["categories"]}')
        chapter_str = valid_filename(f'{param["chapter"]}')
        chapter_dir = os.path.join(Comic.get_full_comicdir(), categories_str, chapter_str)

        param['chapter_dir'] = chapter_dir
        if not os.path.exists(chapter_dir):
            os.makedirs(chapter_dir)

        param['pices_count'] = 0
        # param['pices_datas'] = {}

        self.pices_data = {}

        async def handle_response(response: Response):

            if response.ok:
                if (response.request.resource_type == "image"):

                    # 保存页面上的图像数据
                    await response.finished()
                    imgdata = await response.body()
                    self.pices_data[md5(response.url)] = imgdata

        page.on("response", handle_response)
        await page.goto(url, wait_until='networkidle', timeout=100000)

        await page.wait_for_selector('#mangaFile')

        if await page.query_selector('#checkAdult'):
            await page.click('#checkAdult')

        html = await page.content()
        doc = pq(html)

        cur_idx, page_count = self.get_page_num(doc)
        Logouter.pic_total += page_count
        Logouter.crawlog()

        purls = {}

        self.set_purls(param, doc, cur_idx, purls)

        while True:

            await page.locator('#next').click()

            # await page.wait_for_load_state("networkidle")
            # 等待图片加载完成
            await page.wait_for_selector('#imgLoading', state='hidden')

            html = await page.content()
            doc = pq(html)

            cur_idx, page_count = self.get_page_num(doc)

            self.set_purls(param, doc, cur_idx, purls)

            for urlmd5, pic_fname in purls.copy().items():

                imgdata = self.pices_data.get(urlmd5, None)
                if not imgdata:
                    continue

                if os.path.exists(pic_fname):
                    if PicChecker.valid_pic(pic_fname):
                        self.pices_data.pop(urlmd5)
                        purls.pop(urlmd5)
                        Logouter.pic_crawed += 1
                        Logouter.crawlog()
                        continue
                    else:
                        os.remove(pic_fname)

                with open(pic_fname, 'wb') as f:
                    f.write(imgdata)

                if not PicChecker.valid_pic(pic_fname):
                    os.remove(pic_fname)
                    Logouter.pic_failed += 1
                    Logouter.crawlog()

                    self.pices_data.pop(urlmd5)
                    purls.pop(urlmd5)

                    Logouter.red(f'\n下载失败！下载图片不完整={pic_fname}')
                    continue
                    # raise Exception(f'下载失败！下载图片不完整={pic_fname}')

                self.pices_data.pop(urlmd5)
                purls.pop(urlmd5)

                Logouter.pic_crawed += 1
                Logouter.crawlog()

            if cur_idx >= page_count:  # len(purls) >= page_count:
                downloaded_count = Zipper.count_dir(param['chapter_dir'])

                if downloaded_count >= page_count:
                    break
                else:
                    cur_idx = 1
                    await page.goto(url, wait_until='networkidle', timeout=100000)

        downloaded_count = Zipper.count_dir(param['chapter_dir'])
        if downloaded_count == page_count:

            Zipper.zip(param['chapter_dir'])
            Comic.chapters[md5(url)]['status'] = 1
            Comic.save_to_json()

    def set_purls(self, param, doc, cur_idx, purls):
        purl = doc('#mangaFile').attr('src')
        purl = urllib.parse.quote(purl, safe="[];/?:@&=+$,%")
        purls[md5(purl)] = os.path.join(param['chapter_dir'], f'{str(cur_idx).zfill(4)}.{extrat_extname(purl)}')

    def get_page_num(self, doc):
        count_info = doc('body > div.w980.title > div:nth-child(2) > span').text()
        idxs = re.search(r'\((\d+)/(\d+)\)', count_info)
        cur_idx = int(idxs.group(1))
        page_count = int(idxs.group(2))
        return cur_idx, page_count

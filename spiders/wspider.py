import asyncio
import os
import re
import urllib
import json
import lzstring
from playwright.async_api import async_playwright, BrowserContext, Response
from mods.classes import Config
from mods.logouter import Logouter
from mods.picchecker import PicChecker
from mods.settings import CHROMIUM_USER_DATA_DIR
from mods.utils import extrat_extname, md5, valid_filename
from pyquery import PyQuery as pq
from mods.zipper import Zipper


class WSpider:

    def __init__(self, config, parser) -> None:
        self.config: Config = config
        self.parser = parser
        self.semaphore_crawl = asyncio.Semaphore(self.config.ccount)
        self.browser: BrowserContext = None
        self.pices_data = {}
        self.cover_imgdatas = {}

        self.comic_name = ''
        self.author = ''
        self.intro = ''
        self.cover_url = ''
        self.chapters = {}

    @property
    def full_comic_path(self):
        return os.path.join(self.config.maindir, self.config.comic_dir_name)

    async def get_page(self):
        pages = len(self.browser.pages)

        if pages > 0:
            page = self.browser.pages[0]
        else:
            page = await self.browser.new_page()
        return page

    def save_image(self, urlmd5, pic_name):

        imgdata = self.pices_data.get(urlmd5, None)

        if not imgdata:
            return False

        if os.path.exists(pic_name):
            if PicChecker.valid_pic(pic_name):
                return True
            else:
                os.remove(pic_name)

        with open(pic_name, 'wb') as f:
            f.write(imgdata)

        if not PicChecker.valid_pic(pic_name):
            os.remove(pic_name)
            raise Exception(f'下载失败！下载图片不完整={pic_name}')

            # Logouter.red(f'下载失败！下载图片不完整={pic_name}')
            # return False

        return True

    def save_base_info(self):
        if not self.config.comic_dir_name:
            self.config.comic_dir_name = valid_filename(f'[{self.author}]{self.comic_name}' if self.author else self.comic_name)

        # self.full_comic_path = os.path.join(self.config.maindir, self.config.comic_dir_name)

        if not os.path.exists(self.full_comic_path):
            os.makedirs(self.full_comic_path)

        fjson = os.path.join(self.full_comic_path, f'{self.parser.name}.json')

        data = {
            'comic': self.comic_name,
            'url': self.config.comic_url,
            'author': self.author,
            'intro': self.intro,
            'chapters': self.chapters,
        }

        with open(fjson, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def run(self):
        Logouter.blue(f'开始爬取任务,引擎:{self.parser.name}')
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start_crawl_task())
        Logouter.blue('信息爬取完成!')

    async def start_crawl_task(self):

        async with async_playwright() as p:
            self.browser = await p.chromium.launch_persistent_context(user_data_dir=CHROMIUM_USER_DATA_DIR, headless=self.config.headless, accept_downloads=True, args=['--disable-blink-features=AutomationControlled'])

            # 首页爬取章节
            try:
                # 检测是否登录
                if self.config.checklogin:
                    await self.login()

                # 爬取基本信息和章节
                page = await self.fetch_comic_info()
                await self.fetch_chapters(page)

                #保存基本信息
                self.save_base_info()

                #下载封面
                cover_fname = os.path.join(self.full_comic_path, f'cover.{extrat_extname(self.cover_url)}')
                self.save_image(md5(self.cover_url), cover_fname)

                # 设置日志
                Logouter.comic_name = self.config.comic_dir_name

                # 爬取各个章节
                async_tasks = []
                for _, chapter in self.chapters.items():
                    async_task = asyncio.create_task(self.fetch_pices(chapter))
                    async_tasks.append(async_task)

                await asyncio.gather(*async_tasks)

            finally:
                self.save_base_info()
                await self.browser.close()

    async def login(self):
        pass

    async def fetch_comic_info(self, retry=0):
        try:

            async def handle_response(response: Response):
                if response.ok and (response.request.resource_type == "image"):
                    await response.finished()
                    imgdata = await response.body()
                    self.pices_data[md5(response.url)] = imgdata

            page = await self.get_page()
            page.on("response", handle_response)
            await page.goto(self.config.comic_url, wait_until='networkidle', timeout=100000)

            html = await page.content()
            doc = pq(html)

            self.comic_name = doc('div.book-title>h1').text()
            if self.comic_name is None:
                raise Exception('获取漫画名字失败')
            self.author = doc('div.book-detail.pr.fr > ul> li:nth-child(2)>span:nth-child(2)> a').text()
            self.intro = doc('#intro-cut').text()
            self.cover_url = urllib.parse.urljoin(page.url, doc('p.hcover > img').attr('src'))

            return page

        except Exception as e:
            Logouter.yellow(e)
            nretry = retry
            nretry += 1
            if nretry <= 5:
                Logouter.yellow(f'页面{page.url}打开错误,重试={nretry}')
                await asyncio.sleep(5)
                await self.fetch_comic_info(retry=nretry)
            else:
                Logouter.red(e)
                Logouter.pic_failed += 1
                Logouter.crawlog()
                Logouter.red(f'页面{page.url}打开错误,重试超过最大次数')

    async def fetch_chapters(self, page):

        html = await page.content()
        doc = pq(html)

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

                chapterdata = self.chapters.get(keystr, None)
                if not chapterdata:
                    title = f"{el.attr('title')}({el('span>i').text()})"
                    self.chapters[keystr] = {'categories': categories, 'title': title, 'url': url, 'status': 0}

    async def fetch_pices(self, chapter, retry=0):

        try:
            async with self.semaphore_crawl:
                # 爬取每个章节图片
                categories_str = valid_filename(f'{chapter["categories"]}')
                chapter_str = valid_filename(f'{chapter["title"]}')
                chapter_dir = os.path.join(self.full_comic_path, categories_str, chapter_str)
                test_zip_file = f'{chapter_dir}.zip'

                if os.path.exists(test_zip_file):
                    chapter['status'] = 1

                if chapter['status'] == 1:
                    Logouter.chapter_successed += 1
                    Logouter.crawlog()
                    return

                chapter_dir = os.path.join(self.full_comic_path, valid_filename(f'{chapter["categories"]}'), valid_filename(f'{chapter["title"]}'))
                if not os.path.exists(chapter_dir):
                    os.makedirs(chapter_dir)

                async def handle_response(response: Response):
                    if response.ok:
                        if (response.request.resource_type == "image"):
                            # 保存页面上的图像数据
                            await response.finished()
                            imgdata = await response.body()
                            self.pices_data[md5(response.url)] = imgdata

                page = await self.get_page()
                page.on("response", handle_response)
                purls = {}
                cur_idx = -1

                while True:
                    if cur_idx < 0:
                        await page.goto(chapter['url'], wait_until='networkidle', timeout=100000)
                    else:
                        await page.locator('#next').click()
                    # 等待图片加载完成
                    await page.wait_for_selector('#imgLoading', state='hidden')

                    html = await page.content()
                    doc = pq(html)

                    count_info = doc('body > div.w980.title > div:nth-child(2) > span').text()
                    idxs = re.search(r'\((\d+)/(\d+)\)', count_info)
                    cur_idx = int(idxs.group(1))
                    page_count = int(idxs.group(2))
                    purl = doc('#mangaFile').attr('src')
                    purl = urllib.parse.quote(purl, safe="[];/?:@&=+$,%")
                    purls[md5(purl)] = os.path.join(chapter_dir, f'{str(cur_idx).zfill(4)}.{extrat_extname(purl)}')

                    for urlmd5, pic_fname in purls.copy().items():
                        if self.save_image(urlmd5, pic_fname):
                            Logouter.pic_crawed += 1
                            Logouter.crawlog()
                            self.pices_data.pop(urlmd5)
                            purls.pop(urlmd5)

                    if cur_idx >= page_count:  # len(purls) >= page_count:
                        downloaded_count = Zipper.count_dir(chapter_dir)
                        if downloaded_count >= page_count:
                            break
                        else:
                            cur_idx = 1
                            await page.goto(chapter['url'], wait_until='networkidle', timeout=100000)

                downloaded_count = Zipper.count_dir(chapter_dir)
                if downloaded_count == page_count:
                    Zipper.zip(chapter_dir)
                    self.chapters[md5(chapter['url'])]['status'] = 1
                    self.save_base_info()

        except Exception as e:
            Logouter.yellow(e)
            nretry = retry
            nretry += 1
            if nretry <= 5:
                Logouter.yellow(f'页面{chapter["url"]}打开错误,重试={nretry}')
                await asyncio.sleep(5)
                await self.fetch_pices(chapter, retry=nretry)
            else:
                Logouter.red(e)
                Logouter.pic_failed += 1
                Logouter.crawlog()
                Logouter.red(f'页面{chapter["url"]}打开错误,重试超过最大次数')

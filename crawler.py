import asyncio
import time
from typing import Optional
import fire
import json
import os

from typing import Optional
from mods.classes import ComicInfo
from mods.logouter import Logouter
from mods.picchecker import PicChecker
from mods.settings import CHROMIUM_USER_DATA_DIR, DOWNLOADS_DIR
from playwright.async_api import async_playwright, BrowserContext, Response
from mods.zipper import Zipper
from parser.baozimh_parser import BaozimhParser
from parser.comic18_parser import Comic18Parser
from parser.klmag_parser import KlmagParser
from parser.manhuagui_parser import ManhuaguiParser
from parser.parser import Parser
from mods.utils import extrat_extname, findJsonFile, md5, valid_filename
from parser.rawdevart_parser import RawdevartParser
from parser.xmanhua_parser import XmanhuaParser
from parser.zerobywtxt_parser import ZerobywtxtParser


class Crawler:

    def __init__(self) -> None:
        self.comic_list: Optional[list] = None

        self.comic_url: str = ''
        self.maindir = DOWNLOADS_DIR
        self.comic_dir_name: str = ''
        self.chapters: Optional[dict] = None

        self.browser: Optional[BrowserContext] = None

        self.parser: Parser = Parser()

        self.semaphore_crawl = asyncio.Semaphore(1)

    @property
    def comic_full_dir(self):
        return os.path.join(self.maindir, self.comic_dir_name)

    async def get_page(self):
        pages = len(self.browser.pages)

        if pages > 0:
            page = self.browser.pages[0]
        else:
            page = await self.browser.new_page()
        return page

    def parse_comic_url(self, comic_url):
        if comic_url.endswith('json'):
            with open(comic_url, 'r', encoding='utf-8') as load_f:
                jdata = json.load(load_f)

                self.comic_url = jdata.get('url', None)
                if not self.comic_url:
                    self.comic_url = jdata.get('main_url', None)

                self.maindir = os.path.dirname(os.path.dirname(comic_url))
                self.comic_dir_name = os.path.basename(os.path.dirname(comic_url))
                self.chapters = jdata.get('chapters', {})

        else:
            self.comic_url = comic_url
            self.maindir = DOWNLOADS_DIR
            self.comic_dir_name = ''
            self.chapters = {}

    def gen_parser(self):
        self.parser = Parser()
        if ('manhuagui' in self.comic_url) or ('mhgui' in self.comic_url):
            self.parser = ManhuaguiParser()
        elif '18comic' in self.comic_url:
            self.parser = Comic18Parser()
        elif ('klmag' in self.comic_url) or ('klmanga' in self.comic_url):
            self.parser = KlmagParser()
        elif 'baozimh' in self.comic_url:
            self.parser = BaozimhParser()
        elif 'rawdevart' in self.comic_url:
            self.parser = RawdevartParser()
        elif 'zerobywtxt' in self.comic_url:
            self.parser = ZerobywtxtParser()
        elif 'xmanhua' in self.comic_url:
            self.parser = XmanhuaParser()

    async def handle_response(self, response: Response):
        if response.ok and response.status == 200 and (response.request.resource_type == "image"):

            try:
                # await response.finished()
                imgdata = await response.body()
                self.parser.pices_data[md5(response.url)] = imgdata
            except Exception as e:
                pass
                # Logouter.red(f'response error{e}={response}')

    async def fetch_pices(self, chapter, retry=0):
        page_count = 0
        try:
            async with self.semaphore_crawl:
                # 爬取每个章节图片
                categories_str = valid_filename(f'{chapter["categories"]}')
                chapter_str = valid_filename(f'{chapter["title"]}')
                chapter_dir = os.path.join(self.comic_full_dir, categories_str, chapter_str)
                test_zip_file = f'{chapter_dir}.zip'

                if chapter['status'] == 1:
                    Logouter.chapter_successed += 1
                    Logouter.crawlog()
                    return

                if os.path.exists(test_zip_file):
                    chapter['status'] = 1
                    Logouter.chapter_successed += 1
                    Logouter.crawlog()
                    return

                chapter_dir = os.path.join(self.comic_full_dir, valid_filename(f'{chapter["categories"]}'), valid_filename(f'{chapter["title"]}'))

                page = await self.get_page()
                page_count = await self.parser.parse_chapter_pices(page, chapter, chapter_dir)
                if page_count == Zipper.count_dir(chapter_dir):
                    Zipper.zip(chapter_dir)
                    chapter['status'] = 1
                    Logouter.chapter_successed += 1
                    Logouter.crawlog()
                    self.parser.comic_info.save_data(self.comic_full_dir, self.parser.name)

        except Exception as e:
            Logouter.yellow(e)
            nretry = retry
            nretry += 1
            if nretry <= 5:
                Logouter.yellow(f'页面{chapter["url"]}打开错误,重试={nretry}')
                await asyncio.sleep(5)
                await self.fetch_pices(chapter, retry=nretry)
                Logouter.pic_total -= page_count
            else:
                Logouter.red(e)
                Logouter.pic_failed += 1
                Logouter.crawlog()
                Logouter.red(f'页面{chapter["url"]}打开错误,重试超过最大次数')

    async def fetch_comic_info(self, comic_url, retry=0):
        try:

            page = await self.get_page()
            page.on("response", self.handle_response)
            comic_name, author, intro, cover_url = await self.parser.parse_comic_info(comic_url, page, self.chapters)

            if not self.comic_dir_name:
                self.comic_dir_name = valid_filename(f'[{author}]{comic_name}' if author else comic_name)

            self.parser.comic_info.set_comic_data(comic_name, comic_url, author, intro, self.chapters)
            self.parser.comic_info.save_data(self.comic_full_dir, self.parser.name)

            #下载封面
            self.parser.save_cover(self.comic_full_dir, cover_url)
            Logouter.pic_total += 1
            Logouter.crawlog()

        except Exception as e:
            Logouter.yellow(e)
            nretry = retry
            nretry += 1
            if nretry <= 5:
                Logouter.yellow(f'页面{page.url}打开错误,重试={nretry}')
                await asyncio.sleep(5)
                await self.fetch_comic_info(comic_url, retry=nretry)
            else:
                Logouter.red(e)
                Logouter.pic_failed += 1
                Logouter.crawlog()
                Logouter.red(f'页面{page.url}打开错误,重试超过最大次数')

    async def start_crawl(self, comic_list: list = None, headless=False):
        if comic_list:
            self.comic_list = comic_list
        else:
            self.comic_list = []

        # 运行浏览器
        async with async_playwright() as p:
            self.browser = await p.chromium.launch_persistent_context(user_data_dir=CHROMIUM_USER_DATA_DIR, headless=headless, accept_downloads=True, args=['--disable-blink-features=AutomationControlled'])

            try:

                for comic_url in self.comic_list:

                    if 'manhuagui' in comic_url:

                        start_time = time.time()

                    Logouter.cleardata()
                    # 获得漫画信息
                    self.parse_comic_url(comic_url)
                    if self.comic_url == '' or self.comic_url is None:
                        Logouter.red(f'{comic_url} 解析不到漫画信息')
                        Logouter.comics_successed += 1
                        Logouter.crawlog()
                        continue
                    # 获得parser
                    self.gen_parser()
                    if self.parser.name == 'baseparser':
                        Logouter.red(f'{comic_url} 获取不到解析器')
                        continue

                    # 爬取基本信息和章节信息
                    await self.fetch_comic_info(self.comic_url)
                    Logouter.comic_name = self.comic_dir_name
                    if self.chapters:
                        Logouter.chapter_total = len(self.chapters)
                        Logouter.crawlog()

                        # 爬取各个章节
                        async_tasks = []
                        for _, chapter in self.chapters.items():
                            async_task = asyncio.create_task(self.fetch_pices(chapter))
                            async_tasks.append(async_task)

                        await asyncio.gather(*async_tasks)

                    Logouter.comics_successed += 1
                    Logouter.crawlog()
                    self.parser.comic_info.set_comic_data(chapters=self.chapters)
                    self.parser.comic_info.save_data(self.comic_full_dir, self.parser.name)

                    if 'manhuagui' in comic_url:
                        cost_time = time.time() - start_time
                        await asyncio.sleep(3 - cost_time)

            finally:

                await self.browser.close()


def fetch_mangalist(web):
    if web.startswith('http') or web.endswith('json'):
        return [web]

    tasks: list = []
    if os.path.isdir(web):
        tasks = findJsonFile(web)

    # with open("mangalist.txt", "r", encoding='utf-8') as tf:
    #     lines = tf.read().split('\n')

    # count: int = 0
    # tasks: list = []
    # for jfile in lines:
    #     if web in jfile:
    #         count += 1
    #         tasks.append(jfile)

    return tasks


def run(web='Z:\\medias\\books\\comic\\连载', headless=False, keyword='manhuagui'):
    clist = fetch_mangalist(web)
    Logouter.comics_count = len(clist)
    Logouter.crawlog()

    # loop = asyncio.get_event_loop()
    crawler = Crawler()
    # clist = ['https://tw.manhuagui.com/comic/42311/', "https://tw.manhuagui.com/comic/42314/"]

    # loop.run_until_complete(crawler.start_crawl(clist, headless=headless))
    asyncio.run(crawler.start_crawl(clist, headless=headless))

    Logouter.blue('信息爬取完成!')


if __name__ == "__main__":

    fire.Fire(run)

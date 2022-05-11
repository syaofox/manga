import asyncio
from typing import Optional
import fire
import json
import os

from typing import Optional
from mods.logouter import Logouter
from mods.picchecker import PicChecker
from mods.settings import CHROMIUM_USER_DATA_DIR, DOWNLOADS_DIR
from playwright.async_api import async_playwright, BrowserContext, Response
from parser.manhuagui_parser import ManhuaguiParser
from parser.parser import Parser
from mods.utils import extrat_extname, md5, valid_filename


class Crawler:

    def __init__(self) -> None:
        self.comic_list: Optional[list] = None

        self.comic_url: str = ''
        self.mandir = DOWNLOADS_DIR
        self.comic_dir_name: str = ''
        self.chapters: Optional[dict] = None

        self.browser: Optional[BrowserContext] = None

        self.paser: Parser = Parser()
        self.pices_data: dict = {}

    @property
    def comic_full_dir(self):
        return os.path.join(self.mandir, self.comic_dir_name)

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
                self.maindir = os.path.dirname(os.path.dirname(comic_url))
                self.comic_dir_name = os.path.basename(os.path.dirname(comic_url))
                self.chapters = jdata.get('chapters', {})

        else:
            self.comic_url = comic_url
            self.mandir = DOWNLOADS_DIR
            self.comic_dir_name = ''
            self.chapters = {}

    def gen_parser(self):
        self.paser = Parser()
        if ('manhuagui' in self.comic_url) or ('mhgui' in self.comic_url):
            self.paser = ManhuaguiParser()

    async def handle_response(self, response: Response):
        if response.ok and response.status == 200 and (response.request.resource_type == "image"):

            try:
                # await response.finished()
                imgdata = await response.body()
                self.pices_data[md5(response.url)] = imgdata
            except Exception as e:
                pass
                # Logouter.red(f'response error{e}={response}')

    def save_image(self, urlmd5, pic_name):

        if os.path.exists(pic_name):
            if PicChecker.valid_pic(pic_name):
                return True
            else:
                os.remove(pic_name)

        imgdata = self.pices_data.get(urlmd5, None)

        if not imgdata:
            return False

        with open(pic_name, 'wb') as f:
            f.write(imgdata)

        if not PicChecker.valid_pic(pic_name):
            os.remove(pic_name)
            raise Exception(f'下载失败！下载图片不完整={pic_name}')

        return True

    def save_base_info(self, author, comic_name, intro):

        # self.full_comic_path = os.path.join(self.config.maindir, self.config.comic_dir_name)

        if not os.path.exists(self.comic_full_dir):
            os.makedirs(self.comic_full_dir)

        fjson = os.path.join(self.comic_full_dir, f'{self.paser.name}.json')

        data = {
            'comic': comic_name,
            'url': self.comic_url,
            'author': author,
            'intro': intro,
            'chapters': self.chapters,
        }

        with open(fjson, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    async def fetch_comic_info(self, comic_url, retry=0):
        try:

            page = await self.get_page()
            page.on("response", self.handle_response)
            comic_name, author, intro, cover_url = await self.paser.parse_comic_info(comic_url, page, self.chapters)

            if not self.comic_dir_name:
                self.comic_dir_name = valid_filename(f'[{author}]{comic_name}' if author else comic_name)

            self.save_base_info(author, comic_name, intro)

            #下载封面
            cover_fname = os.path.join(self.comic_full_dir, f'cover.{extrat_extname(cover_url)}')
            self.save_image(md5(cover_url), cover_fname)

            Logouter.comic_name = self.comic_dir_name

            Logouter.chapter_total = len(self.chapters)
            Logouter.crawlog()

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

                    # 获得漫画信息
                    self.parse_comic_url(comic_url)

                    # 获得parser
                    self.gen_parser()

                    # 爬取基本信息和章节信息
                    await self.fetch_comic_info(comic_url)

            finally:
                await self.browser.close()


def run(comic_list_str: str, headless=False, keyword='manhuagui'):

    Logouter.blue(f'开始爬取任务')
    loop = asyncio.get_event_loop()
    crawler = Crawler()
    loop.run_until_complete(crawler.start_crawl([comic_list_str]))
    Logouter.blue('信息爬取完成!')
    # crawler.start_crawl([comic_list_str])


if __name__ == "__main__":

    fire.Fire(run)

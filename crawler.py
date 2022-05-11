from typing import Optional
import fire
import json
import os

from typing import Optional
from mods.settings import DOWNLOADS_DIR
from playwright.async_api import async_playwright, BrowserContext, Response


class Crawler:

    def __init__(self) -> None:
        self.comic_list: Optional[list] = None

        self.comic_url: str = ''
        self.mandir = DOWNLOADS_DIR
        self.comic_dir_name: str = ''
        self.chapters: Optional[dict] = None

        self.browser: Optional[BrowserContext] = None

    @property
    def comic_full_dir(self):
        return os.path.join(self.mandir, self.comic_dir_name)

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

    def start_crawl(self, comic_list: list = None, headless=False):
        if comic_list:
            self.comic_list = comic_list
        else:
            self.comic_list = []

        for comic_url in self.comic_list:
            self.parse_comic_url(comic_url)
            print(self.comic_full_dir)


def run(comic_list_str: str, headless=False, keyword='manhuagui'):
    # comic_list = comic_list_str.split(",")
    crawler = Crawler()

    # with open("mangalist.txt", "r", encoding='utf-8') as tf:
    #     lines = tf.read().split('\n')

    # count: int = 0
    # tasks: list = []
    # for jfile in lines:
    #     if keyword in jfile:
    #         count += 1
    #         tasks.append(jfile)

    # print(f'{keyword} 总共：{len(tasks)}')

    # crawler.start_crawl(tasks)
    crawler.start_crawl([comic_list_str])


if __name__ == "__main__":

    fire.Fire(run)

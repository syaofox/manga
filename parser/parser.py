from mods.classes import ComicInfo
from mods.utils import md5
from playwright.async_api import Page
import os
from mods.logouter import Logouter

from mods.picchecker import PicChecker
from mods.utils import extrat_extname


class Parser:

    def __init__(self) -> None:
        self.pices_data: dict = {}
        self.comic_info = ComicInfo()

    @property
    def name(self):
        return 'baseparser'

    def save_image(self, urlmd5, pic_name):

        if os.path.exists(pic_name):
            if PicChecker.valid_pic(pic_name):
                Logouter.pic_crawed += 1
                Logouter.crawlog()
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

        Logouter.pic_crawed += 1
        Logouter.crawlog()
        if self.pices_data.get(urlmd5, None):
            self.pices_data.pop(urlmd5)

        return True

    async def parse_comic_info(self, comic_url, page: Page, chapters):
        pass

    def save_cover(self, comic_full_dir, cover_url):
        #下载封面
        cover_fname = os.path.join(comic_full_dir, f'cover.{extrat_extname(cover_url)}')
        self.save_image(md5(cover_url), cover_fname)

    async def parse_chapter_pices(self, page, chapter, chapter_dir):
        if not os.path.exists(chapter_dir):
            os.makedirs(chapter_dir)

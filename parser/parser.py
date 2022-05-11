from playwright.async_api import Page
import os

from mods.picchecker import PicChecker


class Parser:

    def __init__(self) -> None:
        pass

    @property
    def name(self):
        return 'baseparser'

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

    async def parse_chapter_pices(self, page, chapter, chapter_dir, save_image):
        if not os.path.exists(chapter_dir):
            os.makedirs(chapter_dir)

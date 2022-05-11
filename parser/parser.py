from playwright.async_api import Page
import os

from mods.picchecker import PicChecker


class Parser:

    def __init__(self) -> None:
        pass

    @property
    def name(self):
        return 'baseparser'

    async def parse_comic_info(self, comic_url, page: Page, chapters):
        pass

    async def parse_chapter_pices(self, page, chapter, chapter_dir, save_image):
        if not os.path.exists(chapter_dir):
            os.makedirs(chapter_dir)

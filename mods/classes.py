from typing import Optional
import os
import json


class Config:

    def __init__(self, comic_url, maindir, comic_dir_name, chapters, ccount=1, headless=False, checklogin=False) -> None:
        """_summary_

        Args:

            ccount (int, optional): 爬取线程数. Defaults to 1.
            dcount (int, optional): 下载线程数. Defaults to 1.
            headless (bool, optional): 无头模式. Defaults to False.
            szip (bool, optional): 跳过压缩. Defaults to False.
            fzip (bool, optional): 强制压缩. Defaults to False.           
        """

        self.ccount = ccount

        self.headless = headless
        self.checklogin = checklogin
        self.comic_url = comic_url
        self.maindir = maindir
        self.comic_dir_name = comic_dir_name
        self.chapters = chapters


class ComicInfo:

    def __init__(self, comic_name='', comic_url='', author='', intro='', chapters: Optional[list] = None) -> None:
        self.comic_name = comic_name
        self.comic_url = comic_url
        self.author = author
        self.intro = intro
        if chapters:
            self.chapters = chapters
        else:
            self.chapters = []

    def set_comic_data(self, comic_name='', comic_url='', author='', intro='', chapters: Optional[list] = None):
        if comic_name: self.comic_name = comic_name
        if comic_url: self.comic_url = comic_url
        if author: self.author = author
        if intro: self.intro = intro
        if chapters: self.chapters = chapters

    def save_data(self, comic_full_dir, fname):

        if not os.path.exists(comic_full_dir):
            os.makedirs(comic_full_dir)

        fjson = os.path.join(comic_full_dir, f'{fname}.json')

        data = {
            'comic': self.comic_name,
            'url': self.comic_url,
            'author': self.author,
            'intro': self.intro,
            'chapters': self.chapters,
        }

        with open(fjson, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
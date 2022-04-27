import json
import os
from mods.classes import Config
from mods.settings import DOWNLOADS_DIR
from mods.utils import valid_filename


class Comic:

    maindir = DOWNLOADS_DIR
    comic_name = ''
    main_url = ''
    author = ''
    intro = ''
    parser_name = ''
    chapters = {}
    comic_dir_name = ''
    pices = {}

    @classmethod
    def load_from_json(cls, fjson):

        with open(fjson, 'r', encoding='utf-8') as load_f:
            jdata = json.load(load_f)

        cls.comic_name = jdata.get('comic', cls.comic_name)
        cls.main_url = jdata.get('url', cls.main_url)
        cls.author = jdata.get('author', cls.author)
        cls.intro = jdata.get('intro', cls.intro)
        cls.chapters = jdata.get('chapters', cls.chapters)

        cls.maindir = os.path.dirname(os.path.dirname(fjson))
        cls.comic_dir_name = os.path.basename(os.path.dirname(fjson))

    @classmethod
    def get_full_comicdir(cls):
        return os.path.join(cls.maindir, cls.gen_comicdir())

    @classmethod
    def get_fjson(cls):
        return os.path.join(cls.maindir, cls.gen_comicdir(), f'{cls.parser_name}.json')

    @classmethod
    def save_to_json(cls):
        full_comicdir = cls.get_full_comicdir()

        fjson = cls.get_fjson()

        if not os.path.exists(full_comicdir):
            os.makedirs(full_comicdir)

        data = {
            'comic': cls.comic_name,
            'url': cls.main_url,
            'author': cls.author,
            'intro': cls.intro,
            'chapters': cls.chapters,
        }

        with open(fjson, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @classmethod
    def set_comic_name(cls, comic_name):
        if cls.comic_name == '':
            cls.comic_name = comic_name

    @classmethod
    def set_author(cls, author):
        if cls.author == '':
            cls.author = author

    @classmethod
    def gen_comicdir(cls):
        if cls.comic_dir_name == "":
            return valid_filename(f'[{cls.author}]{cls.comic_name}' if cls.author else cls.comic_name)
        else:
            return cls.comic_dir_name

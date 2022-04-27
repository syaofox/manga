import fire
from mods.classes import Config

from mods.datamgr import Comic
from parsers.baozimh_parser import BaozimhParser
from parsers.baozimhex_parser import BaozimhexParser
from parsers.comic18_parser import Comic18Paser
from parsers.comic18ex_parser import Comic18exParser
from parsers.klmag_parser import KlmagPaser
from parsers.manhuagui_parser import ManhuaguiPaser
from spiders.spider import Spider


def start_craw(start_url, headless=False, szip=False):

    if start_url.endswith('json'):
        # 加载配置文件
        Comic.load_from_json(start_url)
    else:
        Comic.main_url = start_url

    if ('manhuagui' in Comic.main_url) or ('mhgui' in Comic.main_url):

        parser = ManhuaguiPaser()

        config = Config(parser.name, ccount=1, headless=headless)

    elif ('klmag' in Comic.main_url) or ('klmanga' in Comic.main_url):

        parser = KlmagPaser()
        config = Config(parser.name, ccount=2, headless=headless)

    elif '18comic' in Comic.main_url:

        parser = Comic18exParser()
        config = Config(parser.name, ccount=1, headless=headless)

    elif 'baozimh' in start_url:

        parser = BaozimhexParser()
        config = Config(parser.name, ccount=1, headless=headless)

    if parser == None: return

    Comic.parser_name = parser.name
    spider = Spider(config=config, parser=parser)
    spider.run()


if __name__ == "__main__":
    fire.Fire(start_craw)

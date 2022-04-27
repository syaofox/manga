'''
显示方式	效果	        字体色	    背景色	    颜色描述
0	        终端默认设置	30	40	黑色
1	        高亮显示	    31	41	红色
4	        使用下划线	    32	42	绿色
5	        闪烁	        33	43	黄色
7	        反白显示	    34	44	蓝色
8	        不可见	        35	45	紫红色
                          36	    46	青蓝色
                        37	    47	白色

\033 [显示方式;字体色;背景色m ...... [\033 [0m]
'''
import time


class Logouter:
    comic_name = ''

    chapter_total = 0
    chapter_successed = 0
    chapter_passed = 0

    pic_total = 0
    pic_crawed = 0
    pic_failed = 0

    @classmethod
    def timestr(cls):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    @classmethod
    def red(cls, msg):
        print(f"[{cls.timestr()}]\033[1;31;1m{msg}\033[0m")

    @classmethod
    def blue(cls, msg):
        print(f"[{cls.timestr()}]\033[1;34;1m{msg}\033[0m")

    @classmethod
    def green(cls, msg):
        print(f"[{cls.timestr()}]\033[1;32;1m{msg}\033[0m")

    @classmethod
    def yellow(cls, msg):
        print(f"[{cls.timestr()}]\033[1;33;1m{msg}\033[0m")

    @classmethod
    def crawlog(cls):
        msg = (f'\r[{cls.timestr()}]<\033[1;36;1m{cls.comic_name}\033[0m>章节:\033[1;33;1m{cls.chapter_successed}\033[0m/\033[1;33;1m{cls.chapter_total}\033[0m | '
               f'图片:\033[1;33;1m{cls.pic_crawed}\033[0m/\033[1;33;1m{cls.pic_total}\033[0m 失败:\033[1;31;1m{cls.pic_failed}\033[0m')
        print(msg, end='', flush=True)

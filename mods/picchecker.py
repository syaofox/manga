import imghdr
import os
from PIL import Image


class PicChecker():

    @classmethod
    def valid_jpg(cls, jpg_file):
        with open(jpg_file, 'rb') as f:
            f.seek(-20, 2)
            buf = f.read()
            return buf.find(b'\xff\xd9') >= 0

    @classmethod
    def valid_png(cls, png_file):
        with open(png_file, 'rb') as f:
            f.seek(-20, 2)
            buf = f.read()
            return buf.find(b'\x60\x82') >= 0

    @classmethod
    def valid_pic(cls, pic_file):
        """判断图片是否合法

        Args:
            pic_file (str): 图片文件路径

        Returns:
            bool: 是否合法
        """

        try:
            # pillow判断
            Image.open(pic_file).verify()

            # 图片文件末尾字节判断
            file_type = imghdr.what(pic_file)
            if file_type == 'jpeg' or file_type == 'jpg':
                return cls.valid_jpg(pic_file)
            elif file_type == 'png':
                return cls.valid_png(pic_file)
            else:
                # 未知的一概返回True
                return True
        except Exception:
            return False
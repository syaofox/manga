import os
import shutil
import zipfile

from tqdm import tqdm


class Zipper:

    @staticmethod
    def count_dir(dir):
        return len(os.listdir(dir)) if os.path.exists(dir) else 0

    @staticmethod
    def zips(chapter_dirs, remove_old_files=True):

        for chapter_dir in chapter_dirs:
            with zipfile.ZipFile(chapter_dir + '.zip', 'w', zipfile.ZIP_DEFLATED) as zfile:
                for zdname, _, zfnames in os.walk(chapter_dir):
                    for zfname in tqdm(zfnames, desc=f'压缩 {os.path.basename(zdname)}'):
                        zfile_path = os.path.join(zdname, zfname)
                        zfile.write(zfile_path, zfname)  # 不保存目录结构
            if remove_old_files and os.path.exists(chapter_dir):
                shutil.rmtree(chapter_dir)

    @staticmethod
    def zip(chapter_dir, remove_old_files=True):

        with zipfile.ZipFile(chapter_dir + '.zip', 'w', zipfile.ZIP_DEFLATED) as zfile:
            for zdname, _, zfnames in os.walk(chapter_dir):
                for zfname in tqdm(zfnames, desc=f'压缩 {os.path.basename(zdname)}'):
                    zfile_path = os.path.join(zdname, zfname)
                    zfile.write(zfile_path, zfname)  # 不保存目录结构
        if remove_old_files and os.path.exists(chapter_dir):
            shutil.rmtree(chapter_dir)
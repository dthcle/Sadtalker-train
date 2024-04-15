import os
from tqdm import tqdm
import random
import shutil
from PIL import Image
from src.utils.get_file import Get_img_dirs

def write_txt(dirs, txtdir):  
    with open(txtdir, 'wt') as f_out:
        for i in tqdm(range(len(dirs))):
            content = dirs[i] + ' ' + str(i)
            f_out.write('{:s}\r\n'.format(content))


if __name__ == '__main__':
    root_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "run_cfg")
    preprocess_save_dir = os.path.join(root_path, "preprocess")
    data_dir = os.path.join(preprocess_save_dir, 'images')
    txt_path = os.path.join(preprocess_save_dir, 'images.txt')
    data_dirs = Get_img_dirs(data_dir)
    data_dirs.sort()
    write_txt(data_dirs, txt_path)

        
import os

import config

def init():
    if not os.path.exists(config.files_path):
        os.makedirs(config.files_path)


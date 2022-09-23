import os
from shutil import rmtree

import config
from src.database import Art, session_maker

    
def get_grouped_open_images():
    result = []
    for pack in config.posts_list:
        post = []
        for art in pack:
            path = art[0]
            image = open(path, 'rb')
            post.append(image)
        result.append(post)
    return result


def block_user(user_id):
    with session_maker() as session:
        session.query(Art).filter(Art.author_id == user_id).update({'posted': True})


def del_dir(path):
    if os.path.exists(path):
        rmtree(path)

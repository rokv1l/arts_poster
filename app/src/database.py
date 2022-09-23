from time import sleep

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy import Column, Text, Integer, String, ForeignKey, Float, Boolean, Table, JSON
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base


base = declarative_base()


class Art(base):
    __tablename__ = 'arts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    pixiv_id = Column(Integer)
    art_num = Column(Integer)
    url = Column(String)
    posted = Column(Boolean, default=False)
    author_id = Column(Integer)


while True:
    try:
        engine = create_engine('sqlite:///shows.db')
        base.metadata.create_all(engine)

        session_maker = sessionmaker(bind=engine)
        break
    except OperationalError:
        logger.info('Db connecting error... Trying again')
        sleep(5)

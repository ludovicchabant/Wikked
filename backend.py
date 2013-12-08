import logging
from celery import Celery
from utils import find_wiki_root


logging.basicConfig(level=logging.DEBUG)


app = Celery(
        'wikked',
        broker='amqp://',
        backend='amqp://',
        include=['wikked.tasks'])

if __name__ == '__main__':
    app.start()


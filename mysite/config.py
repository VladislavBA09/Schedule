from os import environ as env


class WeekConfig:
    WEEKDAYS = {
        0: 'Mon',
        1: 'Tue',
        2: 'Wen',
        3: 'Thu',
        4: 'Fri',
        5: 'Sut',
        6: 'Sun'
    }


class TestConfig:
    TESTING = True
    PATH_FILE = 'test_data'
    DATA_BASE = 'sqlite://'


class DefaultConfig:
    DEBUG = True
    DATA_BASE = env.get('DATA_BASE', 'sqlite:///database.db')
    KEY = '0b0894ef8eb159c8c29d59e4c0a72e4d7b9e9dd2af8de6ec'


class Email:
    LOGIN = 'v.brunko99@gmail.com'
    PASSWORD = 'lvoq yetp osor zhmr'
    DATA_SUBJECT = 'Your schedule'
    DATA_BODY = 'From your Schedule Creator'

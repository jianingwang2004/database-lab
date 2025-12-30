# config.py
import os

class Config:
    SECRET_KEY = os.urandom(24)  # 随机生成一个密钥
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:CWxsypl191016@127.0.0.1:3306/lab3'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
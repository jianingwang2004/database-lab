# db_init.py
import mysql.connector
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

db2 = mysql.connector.connect(
    host='127.0.0.1',
    port=3306,
    user='root',
    passwd='CWxsypl191016',
    database='lab3'
)

# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 定义数据库模型
class Teacher(db.Model):
    __tablename__ = '教师'
    工号 = db.Column(db.String(5), primary_key=True)
    姓名 = db.Column(db.String(255))
    密码 = db.Column(db.String(20))
    性别 = db.Column(db.Integer)
    职称 = db.Column(db.Integer)

class Paper(db.Model):
    __tablename__ = '论文'
    序号 = db.Column(db.Integer, primary_key=True, autoincrement=True)
    论文名称 = db.Column(db.String(255), nullable=True)
    发表源 = db.Column(db.String(255), nullable=True)
    发表年份 = db.Column(db.Date, nullable=True)
    类型 = db.Column(db.Integer, nullable=True)
    级别 = db.Column(db.Integer, nullable=True)

class PublishedPaper(db.Model):
    __tablename__ = '发表论文'
    工号 = db.Column(db.String(5), db.ForeignKey('教师.工号'), primary_key=True)
    序号 = db.Column(db.Integer, db.ForeignKey('论文.序号'), primary_key=True)
    排名 = db.Column(db.Integer)
    是否通讯作者 = db.Column(db.Boolean)
    __table_args__ = (
        db.UniqueConstraint('序号', '排名', name='uix_ranking'),
    )

class Project(db.Model):
    __tablename__ = '项目'
    项目号 = db.Column(db.String(255), primary_key=True)
    项目名称 = db.Column(db.String(255))
    项目来源 = db.Column(db.String(255))
    项目类型 = db.Column(db.Integer)
    总经费 = db.Column(db.Float)
    开始年份 = db.Column(db.Integer)
    结束年份 = db.Column(db.Integer)

class UndertakenProject(db.Model):
    __tablename__ = '承担项目'
    工号 = db.Column(db.String(5), db.ForeignKey('教师.工号'), primary_key=True)
    项目号 = db.Column(db.String(255), db.ForeignKey('项目.项目号'), primary_key=True)
    排名 = db.Column(db.Integer)
    承担经费 = db.Column(db.Float)

    __table_args__ = (
        db.UniqueConstraint('项目号', '排名', name='uix_project_ranking'),
    )

class Course(db.Model):
    __tablename__ = '课程'
    课程号 = db.Column(db.String(255), primary_key=True)
    课程名称 = db.Column(db.String(255))
    学时数 = db.Column(db.Integer)
    课程性质 = db.Column(db.Integer)

class TaughtCourse(db.Model):
    __tablename__ = '主讲课程'
    工号 = db.Column(db.String(5), db.ForeignKey('教师.工号'), primary_key=True)
    课程号 = db.Column(db.String(255), db.ForeignKey('课程.课程号'), primary_key=True)
    年份 = db.Column(db.Integer)
    学期 = db.Column(db.Integer)
    承担学时 = db.Column(db.Integer)
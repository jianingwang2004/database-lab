from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from sqlalchemy.exc import IntegrityError
from config import Config
from models import db, Teacher, Paper, PublishedPaper, Project, UndertakenProject, Course, TaughtCourse
from sqlalchemy import func, extract
from io import BytesIO
from fpdf import FPDF
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)  # 加载配置
db.init_app(app)

# 创建数据库表
with app.app_context():
    db.create_all()

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    工号 = request.form['工号']
    密码 = request.form['密码']
    
    teacher = Teacher.query.filter_by(工号=工号, 密码=密码).first()
    if teacher:
        session['工号'] = 工号  # 将工号存储在 session 中
        return redirect(url_for('index'))  # 跳转到功能选择界面
    else:
        flash('该用户不存在，请注册！')
        return redirect(url_for('login'))  # 如果登录失败，返回登录页面

@app.route('/index')
def index():
    if '工号' not in session:
        flash('请先登录！')
        return redirect(url_for('login'))  # 如果用户未登录，跳转到登录页面
    return render_template('index.html')  # 如果用户已登录，显示功能选择界面

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        工号 = request.form['工号']
        姓名 = request.form['姓名']
        密码 = request.form['密码']
        性别 = request.form['性别']
        职称 = request.form['职称']
        
        existing_teacher = Teacher.query.filter_by(工号=工号).first()
        if existing_teacher:
            flash('该用户已存在，请重新注册！')
            return redirect(url_for('register'))
        
        new_teacher = Teacher(工号=工号, 姓名=姓名, 密码=密码, 性别=性别, 职称=职称)
        db.session.add(new_teacher)
        db.session.commit()
        
        flash('注册成功！请登录。')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/add_paper', methods=['GET', 'POST'])
def add_paper():
    if '工号' not in session:
        flash('请先登录！')
        return redirect(url_for('login'))
    
    teacher_id = session['工号']
    
    # 查询该教师的所有论文
    teacher_papers = db.session.query(Paper, PublishedPaper).join(
        PublishedPaper, Paper.序号 == PublishedPaper.序号
    ).filter(PublishedPaper.工号 == teacher_id).all()
    
    if request.method == 'POST':
        # 处理新增论文
        序号 = request.form['序号']
        论文名称 = request.form['论文名称']
        发表源 = request.form['发表源']
        发表年份_str = request.form['发表年份']
        类型 = request.form['类型']
        级别 = request.form['级别']
        排名 = int(request.form['排名'])
        是否通讯作者 = '是否通讯作者' in request.form
        
        # 解析日期字符串为日期对象
        try:
            发表年份 = datetime.strptime(发表年份_str, '%Y-%m-%d').date()
        except ValueError:
            flash('日期格式错误，请使用 YYYY-MM-DD 格式')
            return redirect(url_for('add_paper'))
        
        # 检查序号是否已存在
        paper = Paper.query.get(序号)
        
        if paper:
            # 论文已存在，检查基本信息是否一致
            mismatch = False
            mismatch_fields = []
            
            # 检查论文名称
            if paper.论文名称 != 论文名称:
                mismatch = True
                mismatch_fields.append("论文名称")
            
            # 检查发表源
            if paper.发表源 != 发表源:
                mismatch = True
                mismatch_fields.append("发表源")
            
            # 检查发表年份（只比较年份）
            if paper.发表年份.year != 发表年份.year:
                mismatch = True
                mismatch_fields.append("发表年份")
            
            # 检查类型
            if paper.类型 != int(类型):
                mismatch = True
                mismatch_fields.append("类型")
            
            # 检查级别
            if paper.级别 != int(级别):
                mismatch = True
                mismatch_fields.append("级别")
            
            if mismatch:
                flash(f'该序号已存在，但论文信息不匹配！不匹配字段: {", ".join(mismatch_fields)}')
                return redirect(url_for('add_paper'))
            
            # 检查当前教师是否已登记过该论文
            existing_published = PublishedPaper.query.filter_by(
                工号=teacher_id, 序号=序号
            ).first()
            if existing_published:
                flash('您已经登记过该论文！')
                return redirect(url_for('add_paper'))
        else:
            # 创建新论文
            paper = Paper(
                序号=序号,
                论文名称=论文名称,
                发表源=发表源,
                发表年份=发表年份,
                类型=类型,
                级别=级别
            )
            db.session.add(paper)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash('创建论文失败，请检查序号是否唯一')
                return redirect(url_for('add_paper'))
        
        # 检查排名是否重复
        existing_rank = PublishedPaper.query.filter_by(
            序号=序号, 排名=排名
        ).first()
        if existing_rank:
            flash(f'该论文中排名{排名}已被教师{existing_rank.工号}占用！')
            return redirect(url_for('add_paper'))
        
        # 检查通讯作者是否已存在
        if 是否通讯作者:
            existing_ca = PublishedPaper.query.filter_by(
                序号=序号, 是否通讯作者=True
            ).first()
            if existing_ca:
                # 获取通讯作者姓名
                ca_teacher = Teacher.query.get(existing_ca.工号)
                ca_name = ca_teacher.姓名 if ca_teacher else "未知教师"
                flash(f'该论文已存在通讯作者：{ca_name}！')
                return redirect(url_for('add_paper'))
        
        # 创建发表记录
        new_published = PublishedPaper(
            工号=teacher_id,
            序号=序号,
            排名=排名,
            是否通讯作者=是否通讯作者
        )
        db.session.add(new_published)
        
        try:
            db.session.commit()
            flash('论文登记成功！')
        except IntegrityError as e:
            db.session.rollback()
            if 'uix_ranking' in str(e):
                flash('提交失败：该论文中该排名已被其他教师占用！')
            else:
                flash('数据库错误，请稍后再试！')
        except Exception as e:
            db.session.rollback()
            flash(f'发生错误：{str(e)}')
        
        return redirect(url_for('add_paper'))
    
    return render_template('add_paper.html', papers=teacher_papers)

# 删除论文
@app.route('/delete_paper/<int:paper_id>', methods=['POST'])
def delete_paper(paper_id):
    if '工号' not in session:
        flash('请先登录！')
        return redirect(url_for('login'))
    
    teacher_id = session['工号']
    
    # 检查论文是否属于当前教师
    published_paper = PublishedPaper.query.filter_by(
        工号=teacher_id, 序号=paper_id
    ).first()
    
    if published_paper:
        # 删除发表记录
        db.session.delete(published_paper)
        
        # 检查是否还有其他作者
        other_authors = PublishedPaper.query.filter_by(序号=paper_id).all()
        if not other_authors:
            # 没有其他作者，删除论文
            paper = Paper.query.get(paper_id)
            if paper:
                db.session.delete(paper)
        
        db.session.commit()
        flash('论文删除成功！')
    else:
        flash('无权删除此论文')
    
    return redirect(url_for('add_paper'))

@app.route('/edit_paper/<int:paper_id>', methods=['GET', 'POST'])
def edit_paper(paper_id):
    if '工号' not in session:
        flash('请先登录！')
        return redirect(url_for('login'))
    
    teacher_id = session['工号']
    paper = Paper.query.get_or_404(paper_id)
    published_paper = PublishedPaper.query.filter_by(
        工号=teacher_id, 序号=paper_id
    ).first()
    
    # 检查是否属于当前教师
    if not published_paper:
        flash('无权修改此论文')
        return redirect(url_for('add_paper'))
    
    if request.method == 'POST':
        # 更新发表信息
        new_rank = int(request.form['排名'])
        new_ca = '是否通讯作者' in request.form
        
        # 检查排名是否被占用
        existing_rank = PublishedPaper.query.filter(
            PublishedPaper.序号 == paper_id,
            PublishedPaper.排名 == new_rank,
            PublishedPaper.工号 != teacher_id
        ).first()
        if existing_rank:
            flash(f'该排名已被教师{existing_rank.工号}占用！')
            return render_template('edit_paper.html', paper=paper, published_paper=published_paper)
        
        # 检查通讯作者
        if new_ca and not published_paper.是否通讯作者:
            existing_ca = PublishedPaper.query.filter(
                PublishedPaper.序号 == paper_id,
                PublishedPaper.是否通讯作者 == True,
                PublishedPaper.工号 != teacher_id
            ).first()
            if existing_ca:
                # 获取通讯作者姓名
                ca_teacher = Teacher.query.get(existing_ca.工号)
                ca_name = ca_teacher.姓名 if ca_teacher else "未知教师"
                flash(f'该论文已存在通讯作者：{ca_name}！')
                return render_template('edit_paper.html', paper=paper, published_paper=published_paper)
        
        # 更新记录
        published_paper.排名 = new_rank
        published_paper.是否通讯作者 = new_ca
        db.session.commit()
        flash('论文信息更新成功！')
        return redirect(url_for('add_paper'))
    
    return render_template('edit_paper.html', paper=paper, published_paper=published_paper)

@app.route('/confirm_paper')
def confirm_paper():
    return render_template('confirm_paper.html')

@app.route('/logout')
def logout():
    session.pop('工号', None)  # 清除 session 中的工号
    flash('您已成功登出！')
    return redirect(url_for('login'))  # 跳转到登录页面

@app.route('/add_project', methods=['GET', 'POST'])
def add_project():
    if '工号' not in session:
        flash('请先登录！')
        return redirect(url_for('login'))
    
    teacher_id = session['工号']
    
    # 查询该教师的所有项目 (保持查询功能)
    teacher_projects = db.session.query(Project, UndertakenProject).join(
        UndertakenProject, Project.项目号 == UndertakenProject.项目号
    ).filter(UndertakenProject.工号 == teacher_id).all()
    
    if request.method == 'POST':
        工号 = teacher_id
        项目号 = request.form['项目号']
        项目名称 = request.form['项目名称']
        项目来源 = request.form['项目来源']
        项目类型 = request.form['项目类型']
        承担经费 = float(request.form['承担经费'])
        开始年份 = request.form['开始年份']
        结束年份 = request.form['结束年份']
        排名 = int(request.form['排名'])
        
        # 检查项目是否已存在
        project = Project.query.get(项目号)
        if project:
            # 更新项目信息
            project.项目名称 = 项目名称
            project.项目来源 = 项目来源
            project.项目类型 = 项目类型
            project.开始年份 = 开始年份
            project.结束年份 = 结束年份
        else:
            # 创建新项目
            project = Project(
                项目号=项目号,
                项目名称=项目名称,
                项目来源=项目来源,
                项目类型=项目类型,
                总经费=承担经费,  # 初始值
                开始年份=开始年份,
                结束年份=结束年份
            )
            db.session.add(project)
        
        # 检查教师是否已承担该项目
        undertaken = UndertakenProject.query.filter_by(工号=工号, 项目号=项目号).first()
        
        # 检查排名是否重复（同一项目中）
        existing_rank = UndertakenProject.query.filter_by(
            项目号=项目号, 排名=排名
        ).first()
        if existing_rank and existing_rank.工号 != 工号:
            flash(f'该项目中排名{排名}已被教师{existing_rank.工号}占用！')
            return redirect(url_for('add_project'))
        
        if undertaken:
            # 更新承担记录
            undertaken.承担经费 = 承担经费
            undertaken.排名 = 排名  # 更新排名
        else:
            # 新增承担记录（包含排名）
            undertaken = UndertakenProject(
                工号=工号,
                项目号=项目号,
                承担经费=承担经费,
                排名=排名  # 设置排名
            )
            db.session.add(undertaken)
        
        # 计算所有教师的承担经费总和
        total_funding = db.session.query(
            func.sum(UndertakenProject.承担经费)
        ).filter(
            UndertakenProject.项目号 == 项目号
        ).scalar() or 0.0
        
        # 更新项目总经费
        project.总经费 = total_funding
        
        try:
            db.session.commit()
            flash('项目登记成功！')
        except IntegrityError as e:
            db.session.rollback()
            if 'uix_project_ranking' in str(e.orig):
                flash('提交失败：该项目中该排名已被其他教师占用！')
            else:
                flash('数据库错误，请稍后再试！')
        except Exception as e:
            db.session.rollback()
            flash(f'发生错误：{str(e)}')
        
        return redirect(url_for('add_project'))
    
    # 保持查询功能：返回包含项目列表的模板
    return render_template('add_project.html', projects=teacher_projects)

@app.route('/delete_project/<project_id>', methods=['POST'])
def delete_project(project_id):
    if '工号' not in session:
        flash('请先登录！')
        return redirect(url_for('login'))
    
    teacher_id = session['工号']
    
    # 获取承担记录
    undertaken = UndertakenProject.query.filter_by(工号=teacher_id, 项目号=project_id).first()
    
    if undertaken:
        # 删除承担记录
        db.session.delete(undertaken)
        
        # 重新计算项目总经费
        total_funding = db.session.query(
            func.sum(UndertakenProject.承担经费)
        ).filter(
            UndertakenProject.项目号 == project_id
        ).scalar() or 0.0
        
        # 更新项目总经费
        project = Project.query.get(project_id)
        if project:
            project.总经费 = total_funding
            
            # 如果没有其他承担者，删除项目
            if total_funding == 0:
                db.session.delete(project)
        
        try:
            db.session.commit()
            flash('项目删除成功！')
        except Exception as e:
            db.session.rollback()
            flash(f'删除失败：{str(e)}')
    else:
        flash('无权删除此项目')
    
    return redirect(url_for('add_project'))

@app.route('/edit_project/<project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if '工号' not in session:
        flash('请先登录！')
        return redirect(url_for('login'))
    
    teacher_id = session['工号']
    
    # 检查是否属于当前教师
    undertaken = UndertakenProject.query.filter_by(
        工号=teacher_id, 
        项目号=project_id
    ).first()
    
    if not undertaken:
        flash('无权修改此项目')
        return redirect(url_for('add_project'))
    
    project = Project.query.get(project_id)
    
    if request.method == 'POST':
        # 只更新承担信息（经费和排名）
        new_rank = int(request.form['排名'])
        new_funding = float(request.form['承担经费'])
        
        # 检查新排名是否被占用（除了自己）
        existing_rank = UndertakenProject.query.filter(
            UndertakenProject.项目号 == project_id,
            UndertakenProject.排名 == new_rank,
            UndertakenProject.工号 != teacher_id
        ).first()
        if existing_rank:
            flash(f'该排名已被教师{existing_rank.工号}占用！')
            return render_template('edit_project.html', project=project, undertaken=undertaken)
        
        # 更新记录
        undertaken.承担经费 = new_funding
        undertaken.排名 = new_rank
        
        # 重新计算总经费
        total_funding = db.session.query(
            func.sum(UndertakenProject.承担经费)
        ).filter(
            UndertakenProject.项目号 == project_id
        ).scalar() or 0.0
        
        project.总经费 = total_funding
        
        try:
            db.session.commit()
            flash('项目更新成功！')
            return redirect(url_for('add_project'))
        except IntegrityError as e:
            db.session.rollback()
            if 'uix_project_ranking' in str(e.orig):
                flash('提交失败：该项目中该排名已被其他教师占用！')
            else:
                flash('数据库错误，请稍后再试！')
        except Exception as e:
            db.session.rollback()
            flash(f'发生错误：{str(e)}')
    
    return render_template('edit_project.html', project=project, undertaken=undertaken)

@app.route('/confirm_project')
def confirm_project():
    return render_template('confirm_project.html')

# 登记课程（包含增删改查）
@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if '工号' not in session:
        flash('请先登录！')
        return redirect(url_for('login'))
    
    teacher_id = session['工号']
    
    # 查询该教师的所有课程
    teacher_courses = db.session.query(Course, TaughtCourse).join(
        TaughtCourse, Course.课程号 == TaughtCourse.课程号
    ).filter(TaughtCourse.工号 == teacher_id).all()
    
    if request.method == 'POST':
        工号 = teacher_id
        课程号 = request.form['课程号']
        课程名称 = request.form['课程名称']
        学期 = request.form['学期']
        承担学时 = int(request.form['承担学时'])
        年份 = int(request.form['年份'])
        课程性质 = int(request.form['课程性质'])
        
        # 检查课程是否已存在
        course = Course.query.filter_by(课程号=课程号).first()
        if course:
            # 更新课程信息（名称、课程性质等）
            course.课程名称 = 课程名称
            course.课程性质 = 课程性质
        else:
            # 如果课程不存在，创建新课程（初始学时数=当前教师的承担学时）
            course = Course(
                课程号=课程号,
                课程名称=课程名称,
                学时数=承担学时,  # 初始值
                课程性质=课程性质
            )
            db.session.add(course)
        
        # 检查教师是否已教授该课程
        taught_course = TaughtCourse.query.filter_by(
            工号=工号, 课程号=课程号, 年份=年份, 学期=学期
        ).first()
        if taught_course:
            # 如果已教授，更新承担学时
            taught_course.承担学时 = 承担学时
        else:
            # 如果未教授，新增记录（包含年份和学期）
            taught_course = TaughtCourse(
                工号=工号,
                课程号=课程号,
                年份=年份,
                学期=学期,
                承担学时=承担学时
            )
            db.session.add(taught_course)
        
        # 计算所有教师对该课程的承担学时总和
        total_hours = db.session.query(
            func.sum(TaughtCourse.承担学时)
        ).filter(
            TaughtCourse.课程号 == 课程号
        ).scalar() or 0  # 如果 NULL，默认 0
        
        # 更新课程的学时数
        course.学时数 = total_hours
        db.session.commit()
        flash('课程登记成功！')
        return redirect(url_for('add_course'))
    
    return render_template('add_course.html', courses=teacher_courses)

# 删除课程
@app.route('/delete_course/<course_id>/<int:year>/<int:term>', methods=['POST'])
def delete_course(course_id, year, term):
    if '工号' not in session:
        flash('请先登录！')
        return redirect(url_for('login'))
    
    teacher_id = session['工号']
    
    # 获取授课记录
    taught_course = TaughtCourse.query.filter_by(
        工号=teacher_id, 
        课程号=course_id,
        年份=year,
        学期=term
    ).first()
    
    if taught_course:
        # 删除授课记录
        db.session.delete(taught_course)
        
        # 重新计算总学时
        total_hours = db.session.query(
            func.sum(TaughtCourse.承担学时)
        ).filter(
            TaughtCourse.课程号 == course_id
        ).scalar() or 0
        
        # 更新课程学时数
        course = Course.query.get(course_id)
        course.学时数 = total_hours
        
        # 如果没有其他授课教师，删除课程
        if total_hours == 0:
            db.session.delete(course)
        
        db.session.commit()
        flash('课程删除成功！')
    else:
        flash('无权删除此课程')
    
    return redirect(url_for('add_course'))

# 编辑课程
@app.route('/edit_course/<course_id>/<int:year>/<int:term>', methods=['GET', 'POST'])
def edit_course(course_id, year, term):
    if '工号' not in session:
        flash('请先登录！')
        return redirect(url_for('login'))
    
    teacher_id = session['工号']
    
    # 检查是否属于当前教师
    taught_course = TaughtCourse.query.filter_by(
        工号=teacher_id, 
        课程号=course_id,
        年份=year,
        学期=term
    ).first()
    
    if not taught_course:
        flash('无权修改此课程')
        return redirect(url_for('add_course'))
    
    course = Course.query.get(course_id)
    
    if request.method == 'POST':
        # 更新课程信息
        course.课程名称 = request.form['课程名称']
        course.课程性质 = int(request.form['课程性质'])
        
        # 更新授课信息
        new_hours = int(request.form['承担学时'])
        taught_course.承担学时 = new_hours
        
        # 重新计算总学时
        total_hours = db.session.query(
            func.sum(TaughtCourse.承担学时)
        ).filter(
            TaughtCourse.课程号 == course_id
        ).scalar() or 0
        
        course.学时数 = total_hours
        db.session.commit()
        flash('课程更新成功！')
        return redirect(url_for('add_course'))
    
    return render_template('edit_course.html', course=course, taught_course=taught_course)

@app.route('/query', methods=['GET', 'POST'])
def query():
    if '工号' not in session:
        flash('请先登录！')
        return redirect(url_for('login'))  # 如果用户未登录，跳转到登录页面
    
    if request.method == 'POST':
        工号 = request.form['工号']
        开始年份 = int(request.form['开始年份'])
        结束年份 = int(request.form['结束年份'])
        
        # 查询教师基本信息
        teacher = Teacher.query.filter_by(工号=工号).first()
        if not teacher:
            flash('教师不存在！')
            return redirect(url_for('query'))
        
        # 映射字典
        gender_map = {1: '男', 2: '女'}
        title_map = {
            1: '博士后', 2: '助教', 3: '讲师', 4: '副教授', 5: '特任教授',
            6: '教授', 7: '助理研究员', 8: '特任副研究员', 9: '副研究员',
            10: '特任研究员', 11: '研究员'
        }
        term_map = {1: '春', 2: '夏', 3: '秋'}
        paper_type_map = {
            1: 'Full Paper', 2: 'Short Paper',
            3: 'Poster Paper', 4: 'Demo Paper'
        }
        paper_level_map = {
            1: 'CCF-A', 2: 'CCF-B', 3: 'CCF-C',
            4: '中文CCF-A', 5: '中文CCF-B', 6: '无级别'
        }
        project_type_map = {
            1: '国家级', 2: '省部级', 3: '市厅级',
            4: '企业合作', 5: '其他'
        }
        
        # 查询数据
        papers = db.session.query(Paper, PublishedPaper).join(
            PublishedPaper, Paper.序号 == PublishedPaper.序号
        ).filter(
            PublishedPaper.工号 == 工号,
            extract('year', Paper.发表年份) >= 开始年份,
            extract('year', Paper.发表年份) <= 结束年份
        ).all()
        
        projects = db.session.query(Project, UndertakenProject).join(
            UndertakenProject, Project.项目号 == UndertakenProject.项目号
        ).filter(
            UndertakenProject.工号 == 工号,
            Project.开始年份 <= 结束年份,
            Project.结束年份 >= 开始年份
        ).all()
        
        courses = db.session.query(Course, TaughtCourse).join(
            TaughtCourse, Course.课程号 == TaughtCourse.课程号
        ).filter(
            TaughtCourse.工号 == 工号,
            TaughtCourse.年份 >= 开始年份,
            TaughtCourse.年份 <= 结束年份
        ).all()
        
        # 生成PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font('SimKai', style="", fname=r"C:\Windows\Fonts\SIMKAI.TTF", uni=True)
        pdf.add_font('SimKai', style="B", fname=r"C:\Windows\Fonts\SIMKAI.TTF", uni=True)
        
        # 标题
        pdf.set_font('SimKai', 'B', 16)
        pdf.cell(0, 10, f'教师教学科研工作统计（{开始年份}-{结束年份}）', 0, 1, 'C')
        pdf.ln(10)
        
        # 教师基本信息
        pdf.set_font('SimKai', 'B', 14)
        pdf.cell(0, 10, '教师基本信息', 0, 1)
        pdf.set_font('SimKai', '', 12)
        pdf.cell(0, 10, f"工号：{teacher.工号}  姓名：{teacher.姓名}  性别：{gender_map.get(teacher.性别, '未知')}  职称：{title_map.get(teacher.职称, '未知')}", 0, 1)
        pdf.ln(5)
        
        # 教学情况
        pdf.set_font('SimKai', 'B', 14)
        pdf.cell(0, 10, '教学情况', 0, 1)
        pdf.set_font('SimKai', '', 12)
        if courses:
            for course, taught in courses:
                pdf.cell(0, 10, f"课程号：{course.课程号}", 0, 1)
                pdf.cell(0, 10, f"课程名：{course.课程名称}", 0, 1)
                pdf.cell(0, 10, f"主讲学时：{taught.承担学时}", 0, 1)
                pdf.cell(0, 10, f"学期：{taught.年份}{term_map.get(taught.学期, '')}", 0, 1)
                pdf.ln(5)
        else:
            pdf.cell(0, 10, "无教学记录", 0, 1)
        pdf.ln(5)
        
        # 发表论文情况
        pdf.set_font('SimKai', 'B', 14)
        pdf.cell(0, 10, '发表论文情况', 0, 1)
        pdf.set_font('SimKai', '', 12)
        if papers:
            for i, (paper, pub) in enumerate(papers, 1):
                pdf.cell(0, 10, f"{i}. {paper.论文名称}，{paper.发表源}，{paper.发表年份.year}，{paper_level_map.get(paper.级别, '')}，排名第 {pub.排名}，{'是' if pub.是否通讯作者 else '非'}通讯作者", 0, 1)
            pdf.ln(5)
        else:
            pdf.cell(0, 10, "无论文发表记录", 0, 1)
        pdf.ln(5)
        
        # 承担项目情况
        pdf.set_font('SimKai', 'B', 14)
        pdf.cell(0, 10, '承担项目情况', 0, 1)
        pdf.set_font('SimKai', '', 12)
        if projects:
            for i, (project, under) in enumerate(projects, 1):
                pdf.cell(0, 10, f"{i}. {project.项目名称}，{project.项目来源}，{project_type_map.get(project.项目类型, '')}，{project.开始年份}-{project.结束年份}，总经费：{project.总经费}，承担经费：{under.承担经费}", 0, 1)
            pdf.ln(5)
        else:
            pdf.cell(0, 10, "无项目承担记录", 0, 1)
        
        # 输出PDF
        pdf_output = BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)
        return send_file(
            pdf_output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'教师{工号}_{开始年份}-{结束年份}_教学科研报告.pdf'
        )
    
    return render_template('query.html')

if __name__ == '__main__':
    app.run(debug=True)
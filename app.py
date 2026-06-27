import math
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
import os

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'docx', 'ppt','pptx'}

app.config['SECRET_KEY'] = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# DATABASE MODEL
class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True)

    email = db.Column(db.String(150), unique=True)

    password = db.Column(db.String(100))

    profile_pic = db.Column(
        db.String(300),
        default='default.png'
    )

    files = db.relationship(
        'File',
        backref='owner',
        lazy=True
    )
# FILE MODEL
class File(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    filename = db.Column(db.String(300))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(
    db.DateTime,
    default=datetime.now
)
    downloads = db.Column(db.Integer, default=0)
    


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
def allowed_file(filename):

    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# HOME PAGE
@app.route('/')
def home():
    return render_template('index.html')

# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':


        username = request.form.get('username')

        email = request.form.get('email')

        password = request.form.get('password')

        hashed_password = generate_password_hash(password)

        new_user = User(
            
            username=username,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form.get('username')

        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            login_user(user)

            return redirect(url_for('dashboard'))

    return render_template('login.html')
# DASHBOARD
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():

    if request.method == 'POST':

        file = request.files['file']

        if file and allowed_file(file.filename):
            
            filename = file.filename.encode('utf-8').decode('utf-8')

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            file.save(filepath)

            new_file = File(
               filename=filename,
               user_id=current_user.id
            )

            db.session.add(new_file)
            db.session.commit()
            flash('Fayl uğurla yükləndi!')
        else:
            flash('Bu fayl formatına icazə verilmir!')

    search = request.args.get('search')

    file_type = request.args.get('type')

    if search or file_type:

        query = File.query.filter(
            File.user_id == current_user.id
        )

        if search:

            query = query.filter(
                File.filename.contains(search)
            )

        if file_type == 'image':

            query = query.filter(
                File.filename.endswith(
                    ('.png', '.jpg', '.jpeg')
                )
            )

        elif file_type == 'pdf':

            query = query.filter(
                File.filename.endswith('.pdf')
            )

        elif file_type == 'docx':

            query = query.filter(
                File.filename.endswith('.docx')
            )

        elif file_type == 'ppt':

            query = query.filter(
                File.filename.endswith(
                    ('.ppt', '.pptx')
                )
            )

        user_files = query.all()

    else:

        user_files = File.query.filter_by(
            user_id=current_user.id
        ).all()
     
    for file in user_files:

        filepath = os.path.join(
        app.config['UPLOAD_FOLDER'],
        file.filename
    )

        if os.path.exists(filepath):

          size = os.path.getsize(filepath)

        if size < 1024:
            file.size = f"{size} B"

        elif size < 1024 * 1024:
            file.size = f"{round(size / 1024, 1)} KB"

        else:
            file.size = f"{round(size / (1024 * 1024), 1)} MB"

    total_files = len(user_files)

    return render_template(
     'dashboard.html',
     files=user_files,
     total_files=total_files
)
    
@app.route('/uploads/<filename>')
@login_required
def preview_file(filename):

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename
    )

# DOWNLOAD FILE
@app.route('/download/<filename>')
@login_required
def download(filename):

    file = File.query.filter_by(
        filename=filename,
        user_id=current_user.id
    ).first()

    if file:
        file.downloads += 1
        db.session.commit()

        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            filename,
            as_attachment=True
        )

    return redirect(url_for('dashboard'))

# DELETE FILE
@app.route('/delete/<filename>')
@login_required
def delete(filename):

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if os.path.exists(filepath):
        os.remove(filepath)

    file = File.query.filter_by(
        filename=filename,
        user_id=current_user.id
    ).first()

    if file:
        db.session.delete(file)
        db.session.commit()
        flash('Fayl uğurla silindi!')

    return redirect(url_for('dashboard'))

@app.route('/upload_profile', methods=['POST'])
@login_required
def upload_profile():

    file = request.files['profile_pic']

    if file:

        filename = secure_filename(file.filename)

        filepath = os.path.join(
            'static/profile_pics',
            filename
        )

        file.save(filepath)

        current_user.profile_pic = filename

        db.session.commit()

        flash('Profil şəkli uğurla yeniləndi!')

    return redirect(url_for('dashboard'))

# LOGOUT
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':

    with app.app_context():
        db.create_all()

    app.run(debug=True)
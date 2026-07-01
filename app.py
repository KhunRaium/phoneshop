import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'phone_shop_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'webp'}

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ----------------- DATABASE MODELS -----------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    phone_number = db.Column(db.String(50), nullable=False)
    address = db.Column(db.Text, nullable=False)
    profile_pic = db.Column(db.String(200), default='default_user.png')
    is_admin = db.Column(db.Boolean, default=False)
    orders = db.relationship('Order', backref='buyer', lazy=True)
    repairs = db.relationship('RepairRequest', backref='owner', lazy=True)

class Phone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='Available')
    image_file = db.Column(db.String(200), default='default_phone.png')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    phone_id = db.Column(db.Integer, db.ForeignKey('phone.id'), nullable=False)
    payment_method = db.Column(db.String(50))
    payment_phone = db.Column(db.String(50))
    status = db.Column(db.String(50), default='Pending')

class RepairRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    phone_model = db.Column(db.String(100), nullable=False)
    issue_description = db.Column(db.Text, nullable=False)
    cost = db.Column(db.Integer, default=0)
    days_required = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='Pending') # Pending, Quoted, AcceptedByUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------- ROUTES -----------------

@app.route('/')
def index():
    phones = Phone.query.all()
    return render_template('index.html', phones=phones)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'admin123':
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(username='admin', password='admin123', phone_number='091234567', address='Store Office', is_admin=True)
                db.session.add(admin_user)
                db.session.commit()
            login_user(admin_user)
            return redirect(url_for('admin_dashboard'))
            
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash("Username သို့မဟုတ် Password မှားယွင်းနေပါသည်။")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        phone_number = request.form.get('phone_number')
        address = request.form.get('address')
        
        if User.query.filter_by(username=username).first():
            flash("ဤ Username ရှိပြီးသားဖြစ်၍ တခြားအမည်ပြောင်းပါ။")
            return redirect(url_for('register'))
            
        new_user = User(username=username, password=password, phone_number=phone_number, address=address)
        db.session.add(new_user)
        db.session.commit()
        flash("အကောင့်ဖွင့်ခြင်း အောင်မြင်ပါပြီ။")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/buy/<int:phone_id>', methods=['GET', 'POST'])
def buy_phone(phone_id):
    if not current_user.is_authenticated:
        flash("ဖုန်းဝယ်ယူရန်အတွက် ကျေးဇူးပြု၍ အကောင့်အရင်ဝင်ပေးပါ။")
        return redirect(url_for('login'))
        
    phone = Phone.query.get_or_404(phone_id)
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        payment_phone = request.form.get('payment_phone')
        
        if phone.stock > 0:
            phone.stock -= 1
            if phone.stock == 0:
                phone.status = 'Sold Out'
            
            new_order = Order(user_id=current_user.id, phone_id=phone.id, payment_method=payment_method, payment_phone=payment_phone)
            db.session.add(new_order)
            db.session.commit()
            flash("ဝယ်ယူမှုအောင်မြင်ပါသည်။")
            return redirect(url_for('profile'))
    return render_template('buy.html', phone=phone)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.phone_number = request.form.get('phone_number')
        current_user.address = request.form.get('address')
        
        file = request.files.get('profile_pic')
        if file and allowed_file(file.filename):
            filename = secure_filename(f"user_{current_user.id}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            current_user.profile_pic = filename
            
        db.session.commit()
        flash("Profile ပြင်ဆင်ပြီးပါပြီ။")
        
    orders = Order.query.filter_by(user_id=current_user.id).all()
    repairs = RepairRequest.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', orders=orders, repairs=repairs)

@app.route('/repair', methods=['GET', 'POST'])
@login_required
def repair():
    if request.method == 'POST':
        phone_model = request.form.get('phone_model')
        issue = request.form.get('issue')
        new_repair = RepairRequest(user_id=current_user.id, phone_model=phone_model, issue_description=issue)
        db.session.add(new_repair)
        db.session.commit()
        flash("ဖုန်းပြင် Form တင်ပြီးပါပြီ။")
        return redirect(url_for('profile'))
    return render_template('repair.html')

@app.route('/repair/accept/<int:repair_id>')
@login_required
def accept_repair(repair_id):
    repair_req = RepairRequest.query.get_or_404(repair_id)
    repair_req.status = 'Accepted By User'
    db.session.commit()
    flash("ပြင်ဆင်ရန် သဘောတူညီချက် ပေးပို့ပြီးပါပြီ။")
    return redirect(url_for('profile'))

# ----------------- ADMIN ROUTES -----------------

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin: return "Access Denied"
    phones = Phone.query.all()
    users = User.query.filter_by(is_admin=False).all()
    
    total_users_amount = len(users)
    total_phones_amount = len(phones)
    
    return render_template('admin_dashboard.html', phones=phones, users=users, total_users_amount=total_users_amount, total_phones_amount=total_phones_amount)
# app.py ထဲတွင် ဤ Route အသစ်ကို ထပ်ဖြည့်ပါ
@app.route('/admin/users')
@login_required
def admin_users_list():
    if not current_user.is_admin: 
        return "Access Denied"
    
    # ရိုးရိုး User တွေကိုပဲ စာရင်းဆွဲထုတ်မယ်
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin_users.html', users=users)
@app.route('/admin/add', methods=['POST'])
@login_required
def admin_add_phone():
    if not current_user.is_admin: return "Access Denied"
    name = request.form.get('name')
    category = request.form.get('category')
    price = request.form.get('price')
    stock = int(request.form.get('stock'))
    
    filename = 'default_phone.png'
    file = request.files.get('phone_image')
    if file and allowed_file(file.filename):
        filename = secure_filename(f"phone_{name}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
    new_phone = Phone(name=name, category=category, price=price, stock=stock, image_file=filename)
    db.session.add(new_phone)
    db.session.commit()
    flash("ဖုန်းအသစ်ထည့်ပြီးပါပြီ။")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit/<int:phone_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_phone(phone_id):
    if not current_user.is_admin: return "Access Denied"
    phone = Phone.query.get_or_404(phone_id)
    if request.method == 'POST':
        phone.name = request.form.get('name')
        phone.category = request.form.get('category')
        phone.price = request.form.get('price')
        phone.stock = int(request.form.get('stock'))
        phone.status = 'Available' if phone.stock > 0 else 'Sold Out'
        
        file = request.files.get('phone_image')
        if file and allowed_file(file.filename):
            filename = secure_filename(f"phone_{phone.name}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            phone.image_file = filename
            
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_edit_phone.html', phone=phone)

@app.route('/admin/delete/<int:phone_id>')
@login_required
def admin_delete_phone(phone_id):
    if not current_user.is_admin: return "Access Denied"
    phone = Phone.query.get_or_404(phone_id)
    db.session.delete(phone)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/repairs', methods=['GET', 'POST'])
@login_required
def admin_repairs():
    if not current_user.is_admin: return "Access Denied"
    if request.method == 'POST':
        repair_id = request.form.get('repair_id')
        cost = request.form.get('cost')
        days = request.form.get('days')
        
        repair_req = RepairRequest.query.get(repair_id)
        repair_req.cost = cost
        repair_req.days_required = days
        repair_req.status = 'Quoted'
        db.session.commit()
        
    repairs = RepairRequest.query.all()
    return render_template('admin_repairs.html', repairs=repairs)

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    with app.app_context():
        db.create_all()
    app.run(debug=True)
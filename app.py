import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-before-deploying")
db_url = (os.environ.get("DATABASE_URL") or "sqlite:///ice_nice.db").strip()
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

COUNTRIES = [
"ایالات متحده","بریتانیا","فرانسه","آلمان","ایتالیا","اسرائیل","ژاپن","کره جنوبی","کانادا","ترکیه","لهستان","اسپانیا","هلند","بلژیک","یونان","اوکراین","نروژ","سوئد","فنلاند","دانمارک","پرتغال","رومانی",
"چین","روسیه","هند","برزیل","کره شمالی","آفریقای جنوبی","ایران","پاکستان","عربستان سعودی","مصر","امارات","ونزوئلا","لبنان","اندونزی",
"سوئیس","اتریش","ایرلند","نیوزیلند","مکزیک","آرژانتین","کلمبیا","کوبا","قزاقستان","جمهوری آذربایجان","مراکش","الجزایر","عراق","قطر","کویت","عمان"
]
ORGANIZATIONS = ["حزب‌الله","حماس","حوثی‌ها","طالبان","سپاه پاسداران","سنتکام","واگنر","موساد","هندالا"]
# Public list is a game-facing overall-power reference, not an official universal ranking.
TOP20 = ["ایالات متحده","چین","آلمان","بریتانیا","فرانسه","ژاپن","روسیه","هند","کره جنوبی","کانادا","ایتالیا","اسپانیا","هلند","برزیل","عربستان سعودی","لهستان","ترکیه","اسرائیل","مکزیک","سوئیس"]

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), default="player", nullable=False)
    country_id = db.Column(db.Integer, db.ForeignKey("country.id"), nullable=True)
    balance = db.Column(db.Integer, default=200, nullable=False)
    badges = db.Column(db.String(500), default="", nullable=False)

class Country(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    color = db.Column(db.String(20), default="#718096", nullable=False)
    status = db.Column(db.String(30), default="آزاد 🟢", nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    target = db.Column(db.String(40), default="همه کشورها", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class DiplomaticRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    kind = db.Column(db.String(60), nullable=False)
    details = db.Column(db.Text, default="", nullable=False)
    status = db.Column(db.String(30), default="در انتظار بررسی", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sender = db.relationship("User", backref="diplomatic_requests")

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    item = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class RegisterForm(FlaskForm):
    username = StringField("نام کاربری", validators=[DataRequired(), Length(min=3, max=40)])
    password = PasswordField("گذرواژه", validators=[DataRequired(), Length(min=8, max=128)])
    country = SelectField("کشور", coerce=int, validators=[DataRequired()])
    submit = SubmitField("ساخت حساب")

class LoginForm(FlaskForm):
    username = StringField("نام کاربری", validators=[DataRequired()])
    password = PasswordField("گذرواژه", validators=[DataRequired()])
    submit = SubmitField("ورود")

class NewsForm(FlaskForm):
    title = StringField("عنوان خبر", validators=[DataRequired(), Length(max=160)])
    body = TextAreaField("متن خبر", validators=[DataRequired(), Length(max=10000)])
    target = SelectField("مخاطب", choices=[("همه کشورها","همه کشورها"),("ناتو","ناتو"),("بریکس","بریکس"),("بی‌طرف","بی‌طرف")])
    submit = SubmitField("انتشار خبر")

class DiplomacyForm(FlaskForm):
    kind = SelectField("نوع درخواست", choices=[("مذاکره","پیشنهاد مذاکره"),("پیمان عدم تجاوز","پیمان عدم تجاوز"),("همکاری اقتصادی","همکاری اقتصادی"),("آتش‌بس","آتش‌بس"),("اتحاد","پیشنهاد اتحاد")])
    details = TextAreaField("توضیحات", validators=[Length(max=3000)])
    submit = SubmitField("ثبت درخواست")

class CountryEditForm(FlaskForm):
    country_id = SelectField("کشور", coerce=int, validators=[DataRequired()])
    color = SelectField("رنگ", choices=[("#4f8cff","آبی"),("#e05252","قرمز"),("#29a36a","سبز"),("#8b5cf6","بنفش"),("#ed8b32","نارنجی"),("#d7b52c","زرد"),("#25a9a0","فیروزه‌ای"),("#758195","خاکستری")])
    status = SelectField("وضعیت", choices=[("آزاد 🟢","آزاد 🟢"),("تحت کنترل ❌","تحت کنترل ❌")])
    submit = SubmitField("ذخیره تغییرات")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def admin_required():
    if not current_user.is_authenticated or current_user.role != "admin":
        abort(403)

@app.context_processor
def inject_globals():
    country = db.session.get(Country, current_user.country_id) if current_user.is_authenticated and current_user.country_id else None
    return {"site_name": "ICE Nice", "my_country": country}

@app.route("/")
def index():
    latest_news = News.query.order_by(News.created_at.desc()).limit(5).all()
    return render_template("index.html", news=latest_news, top20=TOP20)

@app.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = RegisterForm()
    form.country.choices = [(c.id,c.name) for c in Country.query.order_by(Country.name).all() if c.owner_id is None]
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data.strip()).first():
            flash("این نام کاربری قبلاً ثبت شده است.", "error")
        elif not form.country.choices:
            flash("فعلاً کشور آزادی برای انتخاب وجود ندارد.", "error")
        elif form.country.data not in [c[0] for c in form.country.choices]:
            flash("کشور انتخابی معتبر نیست.", "error")
        else:
            user = User(username=form.username.data.strip(), password_hash=generate_password_hash(form.password.data), role="player", country_id=form.country.data, balance=200)
            db.session.add(user); db.session.flush()
            country = db.session.get(Country, form.country.data); country.owner_id = user.id
            db.session.commit(); login_user(user)
            flash("حساب ساخته شد.", "success")
            return redirect(url_for("dashboard"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user); return redirect(url_for("dashboard"))
        flash("نام کاربری یا گذرواژه نادرست است.", "error")
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user(); return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    latest_news = News.query.order_by(News.created_at.desc()).limit(8).all()
    my_requests = DiplomaticRequest.query.filter_by(user_id=current_user.id).order_by(DiplomaticRequest.created_at.desc()).limit(5).all()
    return render_template("dashboard.html", news=latest_news, requests=my_requests, top20=TOP20)

@app.route("/countries")
def countries():
    return render_template("countries.html", countries=Country.query.order_by(Country.name).all())

@app.route("/map")
def map_page():
    return render_template("map.html", countries=Country.query.order_by(Country.name).all())

@app.route("/superpowers")
def superpowers():
    return render_template("superpowers.html", top20=TOP20)

@app.route("/news", methods=["GET","POST"])
def news_page():
    form = NewsForm()
    if current_user.is_authenticated and current_user.role == "admin" and form.validate_on_submit():
        db.session.add(News(title=form.title.data.strip(), body=form.body.data.strip(), target=form.target.data))
        db.session.commit(); flash("خبر منتشر شد.", "success"); return redirect(url_for("news_page"))
    items = News.query.order_by(News.created_at.desc()).all()
    return render_template("news.html", news=items, form=form)

@app.route("/diplomacy", methods=["GET","POST"])
@login_required
def diplomacy():
    form = DiplomacyForm()
    if form.validate_on_submit():
        db.session.add(DiplomaticRequest(user_id=current_user.id, kind=form.kind.data, details=form.details.data.strip()))
        db.session.commit(); flash("درخواست ثبت شد.", "success"); return redirect(url_for("diplomacy"))
    if current_user.role == "admin":
        items = DiplomaticRequest.query.order_by(DiplomaticRequest.created_at.desc()).all()
    else:
        items = DiplomaticRequest.query.filter_by(user_id=current_user.id).order_by(DiplomaticRequest.created_at.desc()).all()
    return render_template("diplomacy.html", form=form, requests=items)

@app.route("/shop")
@login_required
def shop():
    items = [("🎗️ نشان CIP",120),("🏅 نشان VIP",70),("📣 خبر برجسته",20),("🎨 بسته شخصی‌سازی",10)]
    purchases = Purchase.query.filter_by(user_id=current_user.id).order_by(Purchase.created_at.desc()).all()
    return render_template("shop.html", items=items, purchases=purchases)

@app.route("/shop/buy/<path:item>", methods=["POST"])
@login_required
def buy(item):
    prices = {"🎗️ نشان CIP":120,"🏅 نشان VIP":70,"📣 خبر برجسته":20,"🎨 بسته شخصی‌سازی":10}
    if item not in prices: abort(404)
    price = prices[item]
    if current_user.balance < price:
        flash("اعتبار کافی نیست.", "error")
    else:
        current_user.balance -= price
        db.session.add(Purchase(user_id=current_user.id, item=item, price=price))
        if item in ("🎗️ نشان CIP","🏅 نشان VIP"):
            current_user.badges = ",".join(filter(None,[current_user.badges,item]))
        db.session.commit(); flash("خرید ثبت شد.", "success")
    return redirect(url_for("shop"))

@app.route("/admin", methods=["GET","POST"])
@login_required
def admin():
    admin_required()
    form = CountryEditForm()
    form.country_id.choices = [(c.id,c.name) for c in Country.query.order_by(Country.name).all()]
    if form.validate_on_submit():
        c = db.session.get(Country, form.country_id.data)
        if c:
            c.color=form.color.data; c.status=form.status.data; db.session.commit()
            flash("تنظیمات کشور ذخیره شد.", "success")
            return redirect(url_for("admin"))
    return render_template("admin.html", form=form, users=User.query.order_by(User.username).all(),
        countries=Country.query.order_by(Country.name).all(),
        requests=DiplomaticRequest.query.order_by(DiplomaticRequest.created_at.desc()).limit(30).all())

@app.route("/admin/request/<int:req_id>", methods=["POST"])
@login_required
def admin_request(req_id):
    admin_required()
    r = db.session.get(DiplomaticRequest, req_id)
    if not r: abort(404)
    status = request.form.get("status","")
    if status in ["در انتظار بررسی","پذیرفته شد","رد شد"]:
        r.status=status; db.session.commit()
    return redirect(url_for("admin"))

@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="به این بخش دسترسی نداری."), 403

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="صفحه پیدا نشد."), 404

def init_db():
    with app.app_context():
        db.create_all()
        for name in COUNTRIES:
            if not Country.query.filter_by(name=name).first():
                db.session.add(Country(name=name))
        db.session.commit()
        admin_name = os.environ.get("ADMIN_USERNAME")
        admin_password = os.environ.get("ADMIN_PASSWORD")
        if admin_name and admin_password and not User.query.filter_by(username=admin_name).first():
            admin_user = User(username=admin_name, password_hash=generate_password_hash(admin_password), role="admin", balance=999999)
            db.session.add(admin_user); db.session.commit()

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)

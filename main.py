# Flask Framework
import flask
from flask import Flask, render_template, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, EmailField, BooleanField, FloatField, IntegerField
from wtforms.validators import DataRequired,NumberRange
# SQL Connection
import psycopg2 as pg2
# Deployment
import gunicorn
# Encryption
import bcrypt
import re

app = Flask(__name__)
app.config["SECRET_KEY"] = "key"


class AddressForm(FlaskForm):
    country_id = SelectField('Group', coerce=int)
    province_id = SelectField('Group', coerce=int)
    region_id = SelectField('Group', coerce=int)


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = StringField("Password", validators=[DataRequired()])
    email = EmailField("Email", validators=[DataRequired()])
    role = SelectField(u'Role', choices=[('customer', 'Customer'), ('barista', 'Barista'), ('cashier', 'Cashier'),
                                         ('manager', 'Manager')])
    terms = BooleanField('I accept', validators=[DataRequired()])


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = StringField("Password", validators=[DataRequired()])


class ShopForm(FlaskForm):
    latitude = FloatField("Latitude", validators=[DataRequired()])
    longitude = FloatField("Latitude", validators=[DataRequired()])
    shop_name = StringField("Shop Name", validators=[DataRequired()])


class FilterForm(FlaskForm):
    coffee_rating = IntegerField("Coffee Rating", validators=[NumberRange(min=0, max=5)])
    service_rating = IntegerField("Service Rating", validators=[NumberRange(min=0, max=5)])
    environment_rating = IntegerField("Environment Rating", validators=[NumberRange(min=0, max=5)])
    overall_rating = IntegerField("Overall Rating", validators=[NumberRange(min=0, max=5)])


@app.route('/', methods=["POST", "GET"])
def index():
    session["login"] = False
    return redirect("/search/0/0/0")


@app.route('/search/<int:country_id>/<int:province_id>/<int:region_id>', methods=["POST", "GET"])
def search(country_id, province_id, region_id):
    current = [1 if var > 0 else 0 for var in [country_id, province_id, region_id]]
    if sum(current) == 0:
        conn = pg2.connect(database='coffee_shop_rating_site', user='postgres', password='Mesecak01')
        cur = conn.cursor()
        cur.execute(f"select * from country")
        countries = cur.fetchall()
        provinces = [[0, "Province"]]
        regions = [[0, "Region"]]
        conn.close()
    elif sum(current) == 1:
        conn = pg2.connect(database='coffee_shop_rating_site', user='postgres', password='Mesecak01')
        cur = conn.cursor()
        cur.execute(f"select * from country where country_id = {country_id}")
        countries = cur.fetchall()
        cur.execute(f"select province_id, province_name from province where country_id = {country_id}")
        provinces = cur.fetchall()
        regions = [[0, "Region"]]
        conn.close()
    elif sum(current) == 2:
        conn = pg2.connect(database='coffee_shop_rating_site', user='postgres', password='Mesecak01')
        cur = conn.cursor()
        cur.execute(f"select * from country where country_id = {country_id}")
        countries = cur.fetchall()
        cur.execute(f"select province_id, province_name from province where province_id = {province_id}")
        provinces = cur.fetchall()
        cur.execute(f"select region_id, region_name from region where province_id = {province_id}")
        regions = cur.fetchall()
        conn.close()
    elif sum(current) == 3:
        conn = pg2.connect(database='coffee_shop_rating_site', user='postgres', password='Mesecak01')
        cur = conn.cursor()
        cur.execute(f"select latlong from region where region_id = {region_id}")
        latlong = cur.fetchall()
        conn.close()
        latlong = latlong[0][0].replace('(', '').replace(')', '').split(",")
        return redirect(f"/lookout/{latlong}/1")

    country_id = province_id = region_id = None
    form = AddressForm()
    form.country_id.choices = [(g[0], g[1]) for g in countries]
    form.province_id.choices = [(g[0], g[1]) for g in provinces]
    form.region_id.choices = [(g[0], g[1]) for g in regions]
    if form.validate_on_submit():
        country_id = form.country_id.data
        province_id = form.province_id.data
        region_id = form.region_id.data
        form.country_id.data = form.province_id.data = form.region_id.data = ""
        return redirect(f"/search/{country_id}/{province_id}/{region_id}")
    return render_template("index.html", form=form, country_id=country_id, province_id=province_id, region_id=region_id,
                           session=session)


@app.route('/lookout/<string:latlong>/<int:page>', methods=["POST", "GET"])
def lookout(latlong, page):
    coffee_rating = service_rating = environment_rating = overall_rating = None
    form = FilterForm()
    conn = pg2.connect(database='coffee_shop_rating_site', user='postgres', password='Mesecak01')
    cur = conn.cursor()
    cur.execute(f"select * from coffee_shop limit 10 offset {page - 1}*10")
    shops = cur.fetchall()
    conn.close()
    if form.validate_on_submit():
        coffee_rating = form.coffee_rating.data
        service_rating = form.service_rating.data
        environment_rating = form.environment_rating.data
        overall_rating = form.overall_rating.data
        form.coffee_rating.data = form.service_rating.data = form.environment_rating.data = form.overall_rating.data = ""

        conn = pg2.connect(database='coffee_shop_rating_site', user='postgres', password='Mesecak01')
        cur = conn.cursor()
        cur.execute(f"select * from coffee_shop where coffee_rating>={coffee_rating} and service_rating>={service_rating}\
                    and environment_rating>={environment_rating} and overall_rating>={overall_rating} limit 10 offset {page - 1}*10")
        shops = cur.fetchall()
        conn.close()

    return render_template("lookout.html", latlong=latlong, shops=shops, page=page, session=session, form=form,
                           coffee_rating=coffee_rating, service_rating=service_rating,
                           environment_rating=environment_rating, overall_rating=overall_rating)


@app.route('/register', methods=["POST", "GET"])
def register():
    username = password = email = role = terms = None
    form = RegisterForm()
    form_state = 0
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data
        role = form.role.data
        form.username.data = form.password.data = form.email.data = form.role.data = form.terms.data = ""

        conn = pg2.connect(database='coffee_shop_rating_site', user='postgres', password='Mesecak01')
        cur = conn.cursor()
        cur.execute(f"select * from site_user where username = '{username}' or email = '{email}' ")
        result = len(cur.fetchall())
        conn.close()
        if result == 0:
            salt = bcrypt.gensalt(12)
            hash = bcrypt.hashpw(password=password.encode("utf-8"), salt=salt)
            conn = pg2.connect(database='coffee_shop_rating_site', user='postgres', password='Mesecak01')
            cur = conn.cursor()
            cur.execute(f"insert into site_user(username,email,salt,hash,role) \
                values('{username}','{email}','{salt.decode('utf-8')}','{hash.decode('utf-8')}', '{role}');")
            conn.commit()
            conn.close()
        else:
            form_state = 1
    return render_template("register.html", form=form, username=username, password=password, email=email, role=role,
                           terms=terms,
                           form_state=form_state, session=session)


@app.route('/login', methods=["POST", "GET"])
def login():
    username = password = None
    form = LoginForm()
    form_state = 0
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        form.username.data = form.password.data = ""

        conn = pg2.connect(database='coffee_shop_rating_site', user='postgres', password='Mesecak01')
        cur = conn.cursor()
        cur.execute(
            f"select user_id, username, email, salt, encode(hash, 'escape') from site_user where username = '{username}'")
        user_info = cur.fetchall()
        conn.close()

        password = password.encode("utf-8")
        salt = user_info[0][3].encode("utf-8")
        hash = bcrypt.hashpw(password=password, salt=salt).decode("utf-8")
        if hash == user_info[0][4]:
            session["login"] = True
            session["user_id"] = user_info[0][0]
            return redirect("/profile")
        else:
            form_state = 1
    return render_template("login.html", form=form, username=username, password=password, form_state=form_state,
                           login=session["login"])


@app.route('/profile', methods=["POST", "GET"])
def profile():
    return render_template("profile.html", session=session)


@app.route('/add_shop', methods=["POST", "GET"])
def add_shop():
    latitude = longitude = shop_name = None
    form = ShopForm()
    if form.validate_on_submit():
        latitude = form.latitude.data
        longitude = form.longitude.data
        shop_name = form.shop_name.data
        form.latitude.data = form.longitude.data = form.shop_name.data = ""

        conn = pg2.connect(database='coffee_shop_rating_site', user='postgres', password='Mesecak01')
        cur = conn.cursor()
        cur.execute(f"insert into coffee_shop(latlong, shop_name) \
            values('{latitude, longitude}','{shop_name}');")
        conn.commit()
        conn.close()
    return render_template("add_shop.html", form=form, latitude=latitude, longitude=longitude, shop_name=shop_name,
                           login=session["login"])


if __name__ == "__main__":
    app.run()

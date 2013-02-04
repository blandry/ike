import settings
import string
import random
import hashlib
import math
import pickle
import json
from flask import Flask, request, jsonify, render_template, url_for, redirect
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user, make_secure_token
from flask.ext.mail import Mail, Message
from werkzeug import check_password_hash, generate_password_hash
from datetime import datetime, timedelta, date
from directions import Directions
import places
from forms import RegistrationForm, UpdateProfileForm, LoginForm

app = Flask(__name__)
app.secret_key = settings.SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = settings.DATABASE
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.setup_app(app)
login_manager.login_view = "login"
app.config.update(settings.SMTP_SETTINGS)
mail = Mail(app)

@login_manager.user_loader
def load_user(id):
    return User.query.get(id)

@app.context_processor
def inject_settings():
    return dict(settings=settings)

class User(db.Model, UserMixin):
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True)
    password = db.Column(db.String(300))
    active = db.Column(db.Boolean)
    
    def __init__(self, email, password, active=False):
        self.email = unicode(email)
        self.password = generate_password_hash(password)
        self.active = active

    def activate(self, token_value):
        for token in self.activationtokens.all():
            if token.check_if_valid(token_value):
                self.active = True
                db.session.commit()
                break
        return self.active

    def update_password(self, new_password):
        self.password = generate_password_hash(new_password)
        db.session.commit()
        return True

    @staticmethod
    def generate_password(size=10, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))

class ActivationToken(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User',  backref=db.backref('activationtokens', lazy='dynamic'))
    duration = db.Column(db.Interval)
    creation_time = db.Column(db.DateTime)
    value = db.Column(db.String(300))

    def __init__(self, user, value=None, seconds_valid=600):
        self.user = user
        self.duration = timedelta(seconds=seconds_valid)
        self.creation_time = datetime.utcnow()
        if not value:
            value = hashlib.sha224(str(random.getrandbits(256))).hexdigest()
            self.value = value

    @property
    def is_expired(self):
        now = datetime.utcnow()
        return ((now-self.creation_time)>self.duration)

    def check_value(self, checked_value):
        return self.value == checked_value

    def check_if_valid(self, checked_value):
        return (not(self.is_expired) and self.check_value(checked_value))

class HotelType(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300))

    def __init__(self, name, id=None):
        self.name = name
        if id:
            self.id = id

class HotelFacility(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300))

    def __init__(self, name, id=None):
        self.name = name
        if id:
            self.id = id

facilities = db.Table('facilities',
                      db.Column('hotel_id', db.Integer, db.ForeignKey('hotel.id')),
                      db.Column('hotel_facility_id', db.Integer, db.ForeignKey('hotel_facility.id'))
)

class Hotel(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    hotelsbase_id = db.Column(db.Integer)
    name = db.Column(db.String(200))
    stars = db.Column(db.Float)
    price = db.Column(db.Integer)
    city = db.Column(db.String(300))
    state = db.Column(db.String(300))
    country_code = db.Column(db.String(100))
    country = db.Column(db.String(200))
    address = db.Column(db.String(300))
    location = db.Column(db.String(300))
    url = db.Column(db.String(500))
    tripadvisor_url = db.Column(db.String(500))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    lat_max = db.Column(db.Float)
    lat_min = db.Column(db.Float)
    lng_max = db.Column(db.Float)
    lng_min = db.Column(db.Float)
    latlng = db.Column(db.Integer)
    hotel_type_id = db.Column(db.Integer, db.ForeignKey('hotel_type.id'))
    hotel_type = db.relationship('HotelType',  backref=db.backref('hotels', lazy='dynamic'))
    chain_id = db.Column(db.Integer)
    rooms = db.Column(db.Integer)
    hotel_facilities = db.relationship('HotelFacility', secondary=facilities, backref=db.backref('hotels', lazy='dynamic'))
    check_in = db.Column(db.String(100))
    check_out = db.Column(db.String(100))
    rating = db.Column(db.Float)

    def __init__(self, values):
        for key, value in values.items():
            if key == "lat":
                self.lat_max = value + settings.HOTEL_COVERAGE_LAT
                self.lat_min = value - settings.HOTEL_COVERAGE_LAT
            if key == "lng":
                self.lng_max = value + settings.HOTEL_COVERAGE_LNG
                self.lng_min = value - settings.HOTEL_COVERAGE_LNG
            setattr(self, key, value)

class Restaurant(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(200))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    name = db.Column(db.String(200))
    rating = db.Column(db.Float)
    address = db.Column(db.String(300))

    def __init__(self, google_id, lat, lng, name, rating, address):
        self.google_id = google_id
        self.lat = lat
        self.lng = lng
        self.name = name
        self.rating = rating
        self.address = address

trips = db.Table('trips',
                 db.Column('trip_id', db.Integer, db.ForeignKey('trip.id')),
                 db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)

class Trip(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300))
    creation_time = db.Column(db.DateTime)
    users = db.relationship('User', secondary=trips, backref=db.backref('trips', lazy='dynamic'))
    start_address = db.Column(db.String(300))
    end_address = db.Column(db.String(300))

    def __init__(self, name, start_address, end_address, users=[]):
        self.name = name
        self.start_address = start_address
        self.end_address = end_address
        self.creation_time = datetime.utcnow()
        self.users = users

class Night(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.Integer)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'))
    trip = db.relationship('Trip',  backref=db.backref('nights', lazy='dynamic'))
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'))
    hotel = db.relationship('Hotel',  backref=db.backref('nights', lazy='dynamic'))
    diner_restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'))
    diner_restaurant = db.relationship('Restaurant',  foreign_keys=[diner_restaurant_id], backref=db.backref('nights_as_diner', lazy='dynamic'))
    breakfast_restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'))
    breakfast_restaurant = db.relationship('Restaurant',  foreign_keys=[breakfast_restaurant_id], backref=db.backref('nights_as_breakfast', lazy='dynamic'))

    def __init__(self, index, trip, hotel=None, diner_restaurant=None, breakfast_restaurant=None):
        self.index = index
        self.trip = trip
        self.hotel = hotel
        self.diner_restaurant = diner_restaurant
        self.breakfast_restaurant = breakfast_restaurant

class Alert():
    def __init__(self, text, header="", type=""):
        self.text = text
        self.header = header
        self.type = type


# # # # # # USER RELATED VIEWS # # # # # # 

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        if not User.query.filter_by(email=unicode(form.email.data)).first():
            user = User(form.email.data, form.password.data)
            activation_token = ActivationToken(user)
            db.session.add(user)
            db.session.add(activation_token)
            db.session.commit()
            email_activation_link(user.email, user.id, activation_token.value)
            form = LoginForm()
            alert = Alert("You have 5 minutes to check your email and confirm your registration.", type="alert-success")
            return render_template('login.html', form=form, alert=alert)
        form.email.errors = ['Email address already registered.']
    return render_template('register.html', form=form)

@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = UpdateProfileForm()
    if form.validate_on_submit():
    	if check_password_hash(current_user.password, form.old_password.data):
            current_user.update_password(form.new_password.data)
            db.session.commit()
            alert = Alert("Your password has been changed.", type="alert-success")
            trips = current_user.trips.all()
            return render_template('my_trips.html', form=form, alert=alert, trips=trips)
        else:
            alert = Alert("Old password not correct.", type="alert-error")
            return render_template('change_password.html', form=form, alert=alert)
    return render_template('change_password.html', form=form)

@app.route("/my-trips", methods=["GET"])
@login_required
def my_trips():
    trips = current_user.trips.all()
    return render_template('my_trips.html', trips=trips)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=unicode(form.email.data)).first()
        if user and check_password_hash(user.password, form.password.data) and user.active:
            login_user(user)
            return redirect(request.args.get("next") or url_for("quick_search"))
        if user: 
            form.password.errors = ['Invalid password.']
            alert = Alert("<a href='%s?id=%s'>Click here to get a new one by email.</a>" % (url_for('send_new_password'), user.id), "Forgot your password?")
            return render_template('login.html', form=form, alert=alert)
        form.email.errors = ['Invalid login information.']
    return render_template('login.html', form=form)

@app.route("/logout", methods=["GET"])
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/activate", methods=["GET"])
def activate_user():
    id = request.args.get("id")
    token_value = request.args.get("token_value")
    if not id or not token_value:
        alert = Alert('Missing activation information.', type='alert-error')
        form = LoginForm()
        return render_template('login.html', form=form, alert=alert)
    user = User.query.get(id)
    if not user:
        alert = Alert('Invalid user id.', type='alert-error')
        form = LoginForm()
        return render_template('login.html', form=form, alert=alert)
    if user.activate(token_value):
        alert = Alert("Your user account has been activated.", type="alert-success")
        form = LoginForm()
        form.email.data = user.email
        return render_template('login.html', form=form, alert=alert)
    alert = Alert("<a href='%s?id=%s'>Send me a new one.</a>" % (url_for('send_activation_link'), user.id), "Invalid or expired activation link", "alert-error")
    form = LoginForm()
    return render_template('login.html', form=form, alert=alert)

@app.route("/send-activation-link", methods=["GET"])
def send_activation_link():
    id = request.args.get("id")
    user = User.query.get(id)
    if not user:
        alert = Alert("Invalid user id.", type="alert-error")
        form = LoginForm()
        return render_template('login.html', form=form, alert=alert)
    activation_token = ActivationToken(user)
    db.session.add(activation_token)
    db.session.commit()
    email_activation_link(user.email, user.id, activation_token.value)
    alert = Alert("Activation link sent.", type="alert-success")
    form = LoginForm()
    return render_template('login.html', form=form, alert=alert)

@app.route("/send-new-password", methods=["GET"])
def send_new_password():
    id = request.args.get("id")
    user = User.query.get(id)
    if not user:
        alert = Alert("Invalid user id.", type="alert-error")
        form = LoginForm()
        return render_template('login.html', form=form, alert=alert)
    new_password = User.generate_password()
    user.update_password(new_password)
    email_new_password(user.email, new_password)
    alert = Alert("New password sent.", type="alert-success")
    form = LoginForm()
    return render_template('login.html', form=form, alert=alert)

def email_activation_link(email, user_id, token_value):
    activation_link = "%s%s?id=%s&token_value=%s" % (settings.HOST_ADDRESS, url_for("activate_user"), user_id, token_value)
    if settings.DEVELOPMENT:
        print "Activation link: %s" % activation_link
    else:
        body = render_template("email/activation.html", activation_link=activation_link)
        msg = Message("Account activation", recipients=[email])
        msg.html = body
        mail.send(msg)

def email_new_password(email, new_password):
    if settings.DEVELOPMENT:
        print "New password: %s" % new_password
    else:
        body = render_template("email/new_password.html", new_password=new_password)
        msg = Message("New password request", recipients=[email])
        msg.html = body
        mail.send(msg)

# # # # # # # # # # # # # # # # # #  


# # # # # # # # # # # # # # # # # #

@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("login"))

@app.route("/quick-search", methods=["GET"])
def quick_search():
    return render_template("quick_search.html")

@app.route("/ajax/quick-search", methods=["POST"])
def ajax_quick_search():
    origin = request.form.get('origin')
    destination = request.form.get('destination')
    max_travel_duration = int(request.form.get('max-travel-duration'))*3600
    budget = int(request.form.get('budget'))
    max_hotel_price = settings.HOTEL_THRESHOLDS.get(budget)
    directions = Directions.generate_from_google(origin, destination)
    corridors = directions.get_corridors(max_travel_duration, settings.DEFAULT_CORRIDOR_DURATION)
    for corridor in corridors:
        corridor.generate_hotels(Hotel, max_hotel_price, settings.DEFAULT_EARLY_WEIGHT, settings.DEFAULT_DETOUR_WEIGHT)
        if len(corridor.hotels) >= settings.NUMBER_OF_HOTELS_RETURNED:
            corridor.hotels = corridor.hotels[:settings.NUMBER_OF_HOTELS_RETURNED]
    return render_template("quick_search_results.html", directions=directions, corridors=corridors)

@app.route("/ajax/restaurant-search", methods=["POST"])
def ajax_restaurant_search():
    hotel_id = request.form.get("hotel_id")
    hotel = Hotel.query.get(int(hotel_id))
    restaurants = places.get_restaurants_from_google(Restaurant, hotel.lat, hotel.lng)
    if len(restaurants) >= settings.NUMBER_OF_RESTAURANTS_RETURNED:
        restaurants = restaurants[:settings.NUMBER_OF_RESTAURANTS_RETURNED]
    for i in range(len(restaurants)):
        if not Restaurant.query.filter_by(google_id=restaurants[i].google_id).first():
            db.session.add(restaurants[i])
            db.session.commit()
        restaurants[i].id = Restaurant.query.filter_by(google_id=restaurants[i].google_id).first().id
    return render_template("restaurant_search_results.html", restaurants=restaurants)

@app.route("/ajax/generate-trip", methods=["POST"])
def generate_trip():
    choices = json.loads(request.form.get("json"))
    name = request.form.get("name")
    start_address = request.form.get("start_address")
    end_address = request.form.get("end_address")
    trip = Trip(name, start_address, end_address)
    db.session.add(trip)
    for night_index in choices.keys():
        night_json = choices.get(night_index)
        if night_json.get("hotel")=="None":
            hotel = None
        else:
            hotel = Hotel.query.get(int(night_json.get("hotel")))
        if night_json.get("diner")=="None":
            diner_restaurant = None
        else:
            diner_restaurant = Restaurant.query.get(int(night_json.get("diner")))
        if night_json.get("breakfast")=="None":
            breakfast_restaurant = None
        else:
            breakfast_restaurant = Restaurant.query.get(int(night_json.get("breakfast")))
        night = Night(int(night_index), trip, hotel, diner_restaurant, breakfast_restaurant)
        db.session.add(night)
    db.session.commit()
    return jsonify({"url": url_for('trip_overview', id=trip.id)})

@app.route("/trip-overview/<id>", methods=["GET"])
def trip_overview(id):
    trip = Trip.query.get(int(id))
    if not trip:
        alert = Alert("We could not find the trip you are looking for.", type="alert-error")
        form = LoginForm()
        return render_template("login.html", form=form, alert=alert)
    return render_template("trip_overview.html", trip=trip)

@app.route("/add-trip/<id>")
@login_required
def add_trip(id):
    trip = Trip.query.get(int(id))
    if not trip:
        alert = Alert("We could not find the trip you are looking for.", type="alert-error")
        form = LoginForm()
        return render_template("login.html", form=form, alert=alert)
    if not (current_user in trip.users):
        trip.users.append(current_user)
    db.session.commit()
    trips = current_user.trips.all()
    return render_template("my_trips.html", trips=trips) 

@app.route("/remove-trip/<id>")
@login_required
def remove_trip(id):
    trip = current_user.trips.filter_by(id=id).first()
    if not trip:
        alert = Alert("We could not find the trip you are looking for.", type="alert-error")
        form = LoginForm()
        return render_template("login.html", form=form, alert=alert)
    trip.users.remove(current_user)
    db.session.commit()
    alert = Alert("Trip successfully removed from your account.", type="alert-success")
    trips = current_user.trips.all()
    return render_template("my_trips.html", trips=trips, alert=alert)


# # # # # # # # # # # # # # # # # #                                                                                                            

@app.route("/generate-test")
def generate_test():
    origin = 'Boston'
    destination = 'Boulder'
    max_travel_duration = 10*3600
    budget = 3
    max_hotel_price = settings.HOTEL_THRESHOLDS.get(budget)
    directions = Directions.generate_from_google(origin, destination)
    corridors = directions.get_corridors(max_travel_duration, settings.DEFAULT_CORRIDOR_DURATION)
    for corridor in corridors:
        corridor.generate_hotels(Hotel, max_hotel_price, settings.DEFAULT_EARLY_WEIGHT, settings.DEFAULT_DETOUR_WEIGHT)
        if len(corridor.hotels) >= settings.NUMBER_OF_HOTELS_RETURNED:
            corridor.hotels = corridor.hotels[:settings.NUMBER_OF_HOTELS_RETURNED]
    with open('data/test.pk', 'wb') as output:
        pickle.dump(directions, output, pickle.HIGHEST_PROTOCOL)
        pickle.dump(corridors, output, pickle.HIGHEST_PROTOCOL)
    return "Success."

@app.route("/ajax/test", methods=["POST"])
def test():
    with open('data/test.pk', 'rb') as input:
        directions = pickle.load(input)
        corridors = pickle.load(input)
    return render_template("quick_search_results.html", directions=directions, corridors=corridors)

# # # # # # # # # # # # # # # # # #                                                                               


if __name__ == '__main__':
    app.run(debug=settings.DEBUG)

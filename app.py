from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///event_management.db'
app.config['SECRET_KEY'] = 'sarah1234'  

db = SQLAlchemy(app)
login_manager = LoginManager(app)
migrate = Migrate(app, db)

# Define database models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # Add an 'is_admin' field to identify admin users
    active = db.Column(db.Boolean(), default=True)  # Add a new column for user activation status

    # Implementing required properties and methods for Flask-Login
    @property
    def is_active(self):
        return self.active

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False)
    cost = db.Column(db.Float, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Routes for authentication
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and user.password == password:
            login_user(user)
            
            # Check if the user is an admin based on their email address
            if email == 'admin@123.com':
                user.is_admin = True
                db.session.commit()  # Save the updated is_admin status
                
            return redirect(url_for('index'))
            
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    date_added = db.Column(db.DateTime, nullable=False)
    cost = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Add user_id column

    event = db.relationship('Event', backref=db.backref('carts', lazy=True))
    user = db.relationship('User', backref=db.backref('carts', lazy=True))

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_total = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), nullable=False, default='Pending')

# Define database operations
def get_all_users():
    return User.query.all()

def create_user(email, password):
    new_user = User(email=email, password=password)
    db.session.add(new_user)
    db.session.commit()
    return new_user

def get_all_events():
    return Event.query.all()

def create_event(name, description, date, cost):
    # Convert the date string to a Python date object
    date_string = request.form['date']
    date_object = datetime.strptime(date_string, '%Y-%m-%d').date()
    new_event = Event(name=name, description=description, date=date_object, cost=cost)
    db.session.add(new_event)
    db.session.commit()
    return new_event

def get_all_cart_items():
    return Cart.query.all()

def add_to_cart(event_id, date_added, cost):
    new_cart_item = Cart(event_id=event_id, date_added=date_added, cost=cost)
    db.session.add(new_cart_item)
    db.session.commit()
    return new_cart_item

def get_all_bookings():
    return Booking.query.all()

def create_booking(cart_total, payment_status):
    new_booking = Booking(cart_total=cart_total, payment_status=payment_status)
    db.session.add(new_booking)
    db.session.commit()
    return new_booking

# Define routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        create_user(email, password)
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event_page():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        date_string = request.form['date']
        # Convert the date string to a Python date object
        date_object = datetime.strptime(date_string, '%Y-%m-%d').date()
        cost = float(request.form['cost'])
        new_event = Event(name=name, description=description, date=date_object, cost=cost)
        db.session.add(new_event)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('create_event.html')

# Route for Cart Page
@app.route('/cart')
@login_required
def cart():
    cart_items = get_all_cart_items()
    return render_template('cart.html', cart_items=cart_items)

# Route for Booking Page
# Route for Booking Page
@app.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    # Retrieve all cart items
    cart_items = get_all_cart_items()
    
    # Calculate total cost
    total_cost = sum(item.cost for item in cart_items)
    
    if request.method == 'POST':
        cart_total = total_cost
        payment_status = request.form['payment_status']
        create_booking(cart_total, payment_status)
        # Optionally, you can clear the cart after successful payment
        # Clearing cart after payment
        Cart.query.delete()
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('booking.html', cart_items=cart_items, total_cost=total_cost)

# Route for displaying all events (event catalog) (accessible only to authenticated users)
@app.route('/events')
def events():
    all_events = Event.query.all()
    return render_template('events.html', all_events=all_events)

@app.route('/add_to_cart/<int:event_id>', methods=['POST'])
@login_required
def add_to_cart(event_id):
    # Step 1: Retrieve the event object from the database
    event = Event.query.get_or_404(event_id)
    # Step 2: Determine the current user
    user = current_user
    # Step 3: Create a new cart item
    new_cart_item = Cart(event_id=event.id, date_added=datetime.now(), cost=event.cost, user_id=user.id)
    # Step 4: Add the cart item to the database session and commit
    db.session.add(new_cart_item)
    db.session.commit()
    return redirect(url_for('events'))  # Redirect to the events page or any other page as needed

# Route for deleting an event (accessible only to admin users)
@app.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    if not current_user.is_admin:
        # Redirect to index or display an error message indicating permission denied
        return redirect(url_for('index'))
    
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return redirect(url_for('events'))



if __name__ == "__main__":
    app.run(debug=True)











# from Flask-MySQLdb import MySQL

# app = Flask(__name__)

# # MySQL Configuration
# app.config['MYSQL_HOST'] = 'localhost'
# app.config['MYSQL_USER'] = 'root'  # Change this to your MySQL username
# app.config['MYSQL_PASSWORD'] = 'root123'  # Change this to your MySQL password
# app.config['MYSQL_DB'] = 'event_management'

# mysql = MySQL(app)
# --- THE FIX: MUST BE AT THE VERY TOP TO PREVENT RENDER ERRORS ---
import eventlet
eventlet.monkey_patch()
# ----------------------------------------------------------------

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)

# --- SECURITY & DATABASE CONFIGURATION ---
# SECRET_KEY is used to encrypt your session (login)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ogwogwo-super-secret-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///garage.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# The password is pulled from Render settings, defaults to Ogwogwo2026
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Ogwogwo2026')

db = SQLAlchemy(app)
# SocketIO configured for real-time alerts on the Admin Panel
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Database Model
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    plate_number = db.Column(db.String(20), nullable=False)
    service_type = db.Column(db.Text, nullable=False) # Changed to Text for long descriptions
    date = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Pending')

# Initialize Database
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        # 1. Combine Names from the new form
        first = request.form.get('first_name', '')
        others = request.form.get('other_names', '')
        full_name = f"{first} {others}".strip()
        
        # 2. Create the Database Entry
        new_booking = Booking(
            customer_name=full_name,
            phone=request.form.get('phone'),
            plate_number=request.form.get('plate'),
            service_type=request.form.get('service'), # The big description box
            date=request.form.get('date')
        )
        db.session.add(new_booking)
        db.session.commit()
        
        # 3. Trigger Real-time Alert for Admin
        socketio.emit('new_booking', {
            'customer': full_name,
            'plate': new_booking.plate_number,
            'service': "New Request Received"
        })
        
        return redirect(url_for('index'))
    return render_template('booking.html')

# --- PROTECTED ADMIN DASHBOARD ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return "<html><body style='background:#1a1a1a;color:red;text-align:center;padding-top:50px;'><h2>Access Denied</h2><a href='/admin' style='color:white;'>Try Again</a></body></html>", 403

    if not session.get('logged_in'):
        return f'''
            <body style="background:#1a1a1a; color:white; display:flex; justify-content:center; align-items:center; height:100vh; font-family:sans-serif; margin:0;">
                <form method="post" style="border:2px solid #444; padding:30px; border-radius:15px; background:#262626; width:300px; text-align:center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                    <h2 style="color:#ffc107; margin-bottom:20px;">Ogwogwo Admin</h2>
                    <input type="password" name="password" placeholder="Admin Password" required 
                           style="padding:12px; width:100%; margin-bottom:20px; background:#333; color:white; border:1px solid #555; border-radius:5px;">
                    <button type="submit" style="width:100%; padding:12px; background:#007bff; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">LOGIN</button>
                    <p style="margin-top:20px; font-size:11px; color:#666;">
                        Forgot? Update <b>ADMIN_PASSWORD</b> on Render.
                    </p>
                </form>
            </body>
        '''
    
    # Load all bookings, newest first
    bookings = Booking.query.order_by(Booking.id.desc()).all()
    return render_template('admin.html', bookings=bookings)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    socketio.run(app, debug=True) 
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ogwogwo-super-secret-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///garage.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Folder to store uploaded garage photos
UPLOAD_FOLDER = 'static/uploads/gallery'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB Limit
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Ogwogwo2026')

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- MODELS ---
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    plate_number = db.Column(db.String(20), nullable=False)
    service_type = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Pending')

class Gallery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))

with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ROUTES ---
@app.route('/')
def index():
    images = Gallery.query.all()
    return render_template('index.html', images=images)

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        full_name = f"{request.form.get('first_name')} {request.form.get('other_names')}"
        new_booking = Booking(
            customer_name=full_name,
            phone=request.form.get('phone'),
            plate_number=request.form.get('plate'),
            service_type=request.form.get('service'),
            date=request.form.get('date')
        )
        db.session.add(new_booking)
        db.session.commit()
        socketio.emit('new_booking', {'customer': full_name, 'plate': new_booking.plate_number})
        return redirect(url_for('index'))
    return render_template('booking.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        return "Access Denied", 403

    if not session.get('logged_in'):
        return render_template('login.html') # Simplified login logic

    bookings = Booking.query.order_by(Booking.id.desc()).all()
    images = Gallery.query.all()
    return render_template('admin.html', bookings=bookings, images=images)

@app.route('/admin/upload', methods=['POST'])
def upload_file():
    if not session.get('logged_in'): return redirect(url_for('admin'))
    
    if 'file' not in request.files: return redirect(request.url)
    file = request.files['file']
    description = request.form.get('description')

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        new_photo = Gallery(filename=filename, description=description)
        db.session.add(new_photo)
        db.session.commit()
        
    return redirect(url_for('admin'))

@app.route('/admin/delete_photo/<int:id>')
def delete_photo(id):
    if not session.get('logged_in'): return redirect(url_for('admin'))
    photo = Gallery.query.get(id)
    if photo:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], photo.filename))
        except:
            pass # File already gone
        db.session.delete(photo)
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    socketio.run(app, debug=True) 
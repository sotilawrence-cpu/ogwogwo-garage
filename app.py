from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ogwogwo_garage_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///garage.db'
db = SQLAlchemy(app)
socketio = SocketIO(app)

# Database Model
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    vehicle = db.Column(db.String(100), nullable=False)
    plate = db.Column(db.String(20), nullable=False)
    service = db.Column(db.String(50), nullable=False)
    issue = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, In Progress, Completed

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        # Create new booking entry
        new_booking = Booking(
            name=request.form['name'],
            phone=request.form['phone'],
            vehicle=request.form['vehicle'],
            plate=request.form['plate'],
            service=request.form['service'],
            issue=request.form['issue'],
            date=request.form['date']
        )
        db.session.add(new_booking)
        db.session.commit()
        
        # Trigger real-time notification for Admin
        socketio.emit('new_booking_alert', {'name': new_booking.name, 'vehicle': new_booking.vehicle})
        return redirect(url_for('index'))
        
    return render_template('booking.html')

@app.route('/admin')
def admin_panel():
    bookings = Booking.query.order_by(Booking.id.desc()).all()
    return render_template('admin.html', bookings=bookings)

@app.route('/update_status/<int:id>/<string:status>')
def update_status(id, status):
    booking = Booking.query.get(id)
    if booking:
        booking.status = status
        db.session.commit()
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    socketio.run(app, debug=True)
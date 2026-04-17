from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, send, join_room, emit
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'itschat_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///itschat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(100), nullable=False) # 'World' ya 'UserA_UserB'
    sender = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/')
def chat():
    if 'user' not in session:
        return redirect('/login')
    users = User.query.filter(User.username != session['user']).all()
    return render_template('chat.html', username=session['user'], users=users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, password=password)
            db.session.add(user)
            db.session.commit()
        session['user'] = user.username
        return redirect('/')
    return '''<form method="POST"><input name="username" placeholder="Name"><input name="password" type="password"><button>Login</button></form>'''

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    # Purane messages nikaalo
    old_messages = ChatMessage.query.filter_by(room=room).order_by(ChatMessage.timestamp.asc()).all()
    for m in old_messages:
        emit('message', f"<b>{m.sender}:</b> {m.message}")

@socketio.on('private_message')
def handle_private_message(data):
    room = data['room']
    msg_text = data['msg']
    username = session.get('user')
    # Save to DB
    new_msg = ChatMessage(room=room, sender=username, message=msg_text)
    db.session.add(new_msg)
    db.session.commit()
    emit('message', f"<b>{username}:</b> {msg_text}", to=room)

@socketio.on('message')
def handle_world_message(msg):
    username = session.get('user')
    # Save to DB
    new_msg = ChatMessage(room='World', sender=username, message=msg)
    db.session.add(new_msg)
    db.session.commit()
    send(f"<b>{username}:</b> {msg}", broadcast=True)

if __name__ == '__main__':
    socketio.run(app)

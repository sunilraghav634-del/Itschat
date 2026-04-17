from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, send, join_room, leave_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'itschat_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///itschat.db'
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

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
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        
        if not user:
            user = User(username=username, password=password)
            db.session.add(user)
            db.session.commit()
            
        session['user'] = user.username
        return redirect('/')
    
    return '''
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <h2 style="text-align:center; font-family:sans-serif;">ItsChat Login</h2>
    <form method="POST" style="display:flex; flex-direction:column; max-width:300px; margin:auto;">
        <input type="text" name="username" placeholder="Username" required style="padding:10px; margin-bottom:10px;"><br>
        <input type="password" name="password" placeholder="Password" required style="padding:10px; margin-bottom:10px;"><br>
        <button type="submit" style="padding:10px; background:#2980b9; color:white; border:none;">Enter Chat</button>
    </form>
    '''

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)

@socketio.on('private_message')
def handle_private_message(data):
    room = data['room']
    msg = data['msg']
    username = session.get('user', 'Anonymous')
    full_message = f"<b>{username}:</b> {msg}"
    # Send message only to the specific room
    emit('message', full_message, to=room)

@socketio.on('message')
def handle_world_message(msg):
    username = session.get('user', 'Anonymous')
    full_message = f"<b>{username}:</b> {msg}"
    send(full_message, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)

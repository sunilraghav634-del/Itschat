from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, send, join_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'itschat_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///itschat.db'
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=False)
    receiver = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)

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

@app.route('/get_messages/<receiver>')
def get_messages(receiver):
    username = session.get('user')
    if not username:
        return jsonify({"messages": []})
        
    if receiver == 'World':
        messages = Message.query.filter_by(receiver='World').all()
    else:
        messages = Message.query.filter(
            ((Message.sender == username) & (Message.receiver == receiver)) |
            ((Message.sender == receiver) & (Message.receiver == username))
        ).all()
        
    return jsonify({"messages": [{"sender": m.sender, "content": m.content} for m in messages]})

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)

@socketio.on('private_message')
def handle_private_message(data):
    room = data['room']
    msg = data['msg']
    receiver = data['receiver']
    username = session.get('user', 'Anonymous')
    
    new_msg = Message(sender=username, receiver=receiver, content=msg)
    db.session.add(new_msg)
    db.session.commit()
    
    full_message = f"<b>{username}:</b> {msg}"
    emit('message', full_message, to=room)

@socketio.on('message')
def handle_world_message(msg):
    username = session.get('user', 'Anonymous')
    
    new_msg = Message(sender=username, receiver='World', content=msg)
    db.session.add(new_msg)
    db.session.commit()
    
    full_message = f"<b>{username}:</b> {msg}"
    send(full_message, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
    

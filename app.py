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
    
    # Proper HTML Structure with <head> for Google Verification
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>ItsChat Login</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="google-site-verification" content="qQt9M9rKVhv3y69fc4fMKocVlxAk3wb8Br7-T1riv8k" />
    </head>
    <body style="font-family:sans-serif; background-color:#ece5dd; display:flex; flex-direction:column; align-items:center; justify-content:center; height:100vh; margin:0;">
        <h2>ItsChat Login</h2>
        <form method="POST" style="display:flex; flex-direction:column; width:80%; max-width:300px; background:white; padding:20px; border-radius:10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <input type="text" name="username" placeholder="Username" required style="padding:12px; margin-bottom:15px; border:1px solid #ccc; border-radius:5px;">
            <input type="password" name="password" placeholder="Password" required style="padding:12px; margin-bottom:15px; border:1px solid #ccc; border-radius:5px;">
            <button type="submit" style="padding:12px; background:#128c7e; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">Enter Chat</button>
        </form>
    </body>
    </html>
    '''

@app.route('/get_messages/<receiver>')
def get_messages(receiver):
    username = session.get('user')
    if not username: return jsonify({"messages": []})
    if receiver == 'World':
        messages = Message.query.filter_by(receiver='World').all()
    else:
        messages = Message.query.filter(((Message.sender == username) & (Message.receiver == receiver)) | ((Message.sender == receiver) & (Message.receiver == username))).all()
    return jsonify({"messages": [{"sender": m.sender, "content": m.content} for m in messages]})

@socketio.on('join')
def on_join(data):
    join_room(data['room'])

@socketio.on('private_message')
def handle_private_message(data):
    new_msg = Message(sender=session.get('user'), receiver=data['receiver'], content=data['msg'])
    db.session.add(new_msg)
    db.session.commit()
    emit('message', f"<b>{session.get('user')}:</b> {data['msg']}", to=data['room'])

@socketio.on('message')
def handle_world_message(msg):
    new_msg = Message(sender=session.get('user'), receiver='World', content=msg)
    db.session.add(new_msg)
    db.session.commit()
    send(f"<b>{session.get('user')}:</b> {msg}", broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
    

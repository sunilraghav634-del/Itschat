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

# --- PWA Routes ---
@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "ItsChat",
        "short_name": "ItsChat",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ece5dd",
        "theme_color": "#128c7e",
        "icons": [
            {
                "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/Circle-icons-chat.svg/192px-Circle-icons-chat.svg.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/Circle-icons-chat.svg/512px-Circle-icons-chat.svg.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

@app.route('/sw.js')
def sw():
    js = '''
    self.addEventListener('install', (e) => { console.log('PWA Installed'); });
    self.addEventListener('fetch', (e) => { e.respondWith(fetch(e.request).catch(() => new Response('Offline'))); });
    '''
    return app.response_class(js, mimetype='application/javascript')
# ------------------

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
    <!DOCTYPE html>
    <html>
    <head>
        <title>ItsChat Login</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="google-site-verification" content="qQt9M9rKVhv3y69fc4fMKocVlxAk3wb8Br7-T1riv8k" />
        
        <link rel="manifest" href="/manifest.json">
        <meta name="theme-color" content="#128c7e">
        
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #ece5dd; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .login-card { background: white; padding: 40px 30px; border-radius: 15px; box-shadow: 0 10px 20px rgba(0,0,0,0.1); width: 100%; max-width: 350px; text-align: center; }
            .login-card h2 { color: #075e54; margin-bottom: 30px; font-size: 28px; }
            input { width: 85%; padding: 15px; margin-bottom: 20px; border: 1px solid #ddd; border-radius: 8px; font-size: 16px; transition: 0.3s; }
            input:focus { border-color: #128c7e; outline: none; box-shadow: 0 0 5px rgba(18, 140, 126, 0.3); }
            button { width: 95%; padding: 15px; background: #128c7e; color: white; border: none; border-radius: 8px; font-size: 18px; font-weight: bold; cursor: pointer; transition: 0.3s; }
            button:hover { background: #075e54; }
        </style>
    </head>
    <body>
        <div class="login-card">
            <h2>ItsChat</h2>
            <form method="POST">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Join Chat</button>
            </form>
        </div>
        
        <script>
            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.register('/sw.js')
                .then(() => console.log("PWA Ready on Login"));
            }
        </script>
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
    

from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_required, current_user, login_required
from flask_admin import Admin
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_admin.contrib.sqla import ModelView
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import PasswordField

import os

# Initialize the Flask application
app = Flask(__name__,template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY','fallback_key') #needs to be changed and is used for cross-site requests
admin = Admin() #admin page initialization, using bootstrap as templates

# Configure the SQLAlchemy part of the app to use a SQLite database
with app.app_context():
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
    db = SQLAlchemy(app)
    socketio = SocketIO(app)
    admin.init_app(app)

#lobbies for holding players in
    lobbies = {}

#table for users and roles

    class userlist(db.Model):
        __tablename__ = 'users'
        id = db.Column(db.Integer, primary_key=True)
        Name = db.Column(db.String, unique=True, nullable=False)
        Role = db.Column(db.String, unique=False, nullable=False) #make the user a admin or player
        Password = db.Column(db.String, unique=False, nullable=False)
        Highscore = db.Column(db.Integer, unique=False, nullable=True)
        Currentscore = db.Column(db.Integer, unique=False, nullable=True)

        def __init__(self, Name, Role, Password, Highscore, Currentscore):
            self.Name = Name
            self.Role = Role
            self.Password = generate_password_hash(Password)
            self.Highscore = Highscore
            self.Currentscore = Currentscore
            
        def verify_password(self, password):
            return check_password_hash(self.Password, password)


    # Create the database and tables
    db.create_all()


class UserListModelView(ModelView):
    column_exclude_list = ['Password']
    
    # Use a password field for updates
    form_extra_fields = {
        'Password': PasswordField('New Password')  # PasswordField hides input and allows for hashing
    }
    # Override the on_model_change method to hash passwords
    def on_model_change(self, form, model, is_created):
        if form.Password.data:  # Only hash if a password is provided
            model.Password = generate_password_hash(form.Password.data)
        super(UserListModelView, self).on_model_change(form, model, is_created)

admin.add_view(UserListModelView(userlist, db.session))

users = [
    userlist(Name='player1',Password='password123',Role='player',Highscore="", Currentscore=0),
    userlist(Name='player2',Password='password123',Role='player',Highscore="", Currentscore=0),
    userlist(Name='admin1',Password='adminpass',Role='admin',Highscore="", Currentscore=0)
]

with app.app_context():
    if not userlist.query.first():  # Check if any users exist
        db.session.add_all(users)

    db.session.commit()

@app.route('/')
def home():
    return render_template('loginpage.html')

@app.route('/loginpage', methods=['POST'])
def loginpage():
    data = request.get_json() 
    #print(data)
    username = data.get('username')
    password = data.get('password')
    #print(f"Username: {username}, Password: {password}, Role: {role}") #debug stuff again
    
    # Authenticate user
    user = userlist.query.filter_by(Name=username).first()
    if not user or not user.verify_password(password):
        return 'Invalid credentials', 401
    
        # Create a session for the logged-in user
    session['username'] = user.Name
    session['role'] = user.Role
        
        # Redirect based on role
    if user and user.Role == 'admin':
        return url_for('admin')
    else:
        return url_for('menu')
    
#check to see if viewing the page is allowed
@app.route('/admin')
def admin():
    if session.get('role') == 'admin':
        return redirect("/admin/")
    return "Access Denied", 403


@app.route('/signin')
def signin():
    return render_template('signinpage.html')

@app.route('/menu')
def menu():
    if 'username' not in session:
       return redirect(url_for('home'))
    #temporarly changed to game for testng should be menu
    return render_template('game.html',username="placeholder")

@app.route('/tutorial')
def tutorial():
    return render_template('gametutorial.html')

@app.route('/logout')
def logout():
    if 'username' in session:
        session.pop('username', None)  # Remove the username from the session
    
    if 'role' in session:
        session.pop('role', None)  # Remove the username from the session
    return redirect(url_for('home'))  # Redirect to login page


# SocketIO event handlers for game logic
@socketio.on('connect')
def handle_connect():
    username = session.get('username')
    if username:
        emit('message', f'Welcome {username} to the game!')

@socketio.on('join_game')
def handle_join_game():
    username = session.get('username')
    
    # Find an available lobby or create a new one
    lobby_found = False
    for lobby, players in lobbies.items():
        if username in players: #check if already in room
            emit('message', f'You already joined a lobby')
            return
        
        if len(players) < 2:
            lobbies[lobby].append(username)
            join_room(lobby)
            lobby_found = True
            emit('message', f'You joined lobby {lobby} as Player {len(players)+1}.')
            emit('message', f'Player {username} joined the lobby.', room=lobby)
            break
    
    # If no available lobby, create a new one
    if not lobby_found:
        new_lobby = len(lobbies) + 1  # Create a new lobby number
        lobbies[new_lobby] = [username]
        join_room(new_lobby)
        emit('message', f'You created and joined new lobby {new_lobby} as Player 1.')
    
    print(f"Lobbies: {lobbies}")

@socketio.on('move')
def handle_move(data):
    username = session.get('username')
    lobby = get_user_lobby(username)
    
    if lobby:
        print(f"Player {username} moved: {data}")
        emit('move', data, room=lobby)  # Broadcast the move to everyone in the same lobby
    else:
        emit('message', "You are not in a game lobby.")

@socketio.on('leave_game')
def handle_leave_game():
    username = session.get('username')
    """Handles a player leaving a game lobby"""
    # Find the player's current room and remove them
    for room, players in lobbies.items():
        if username in players:
            players.remove(username)
            leave_room(room)  # Remove the player from the room
            emit('message', f'{username} left the room', room=room)  # Notify others in the room
            if len(players) == 0:  # If the room is empty, delete the room
                del lobbies[room]
            break

@socketio.on('disconnect')
def handle_disconnect():
    """Handles a client disconnecting"""
    username = session.get('username')
    if username:
        handle_leave_game(username)

# Helper function to get the lobby of a user
def get_user_lobby(username):
    for lobby, players in lobbies.items():
        if username in players:
            return lobby
    return None

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Default to 5000 if PORT isn't set
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug_mode)
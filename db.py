from flask_sqlalchemy import SQLAlchemy
from app import app

# Set up the database
db = SQLAlchemy(app)

app.app_context().push()

class users(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(100))
    name = db.Column( db.String(100))

    def __init__(self, spotify_id, name):
        self.spotify_id = spotify_id
        self.name = name

class playlists(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(100), db.ForeignKey('users.spotify_id'))
    playlist_id = db.Column(db.String(250))
    song_count = db.Column(db.Integer)

    def __init__(self, spotify_id, playlist_id, song_count):
        self.spotify_id = spotify_id
        self.playlist_id = playlist_id
        self.song_count = song_count
import os
import requests
import urllib.parse
from datetime import datetime
from flask import Flask, redirect, request, jsonify, session, render_template

# Load environment variables
SONG_LIMIT = 20
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

# Spotify API URLs
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/me'

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

def get_token(grant_type: str, code: str = None, refresh_token: str = None):
    """
        Get the refresh token and/or access token from Spotify API depending on the grant type and the arguments provided.
        Provide the code and grant_type = "authorization_code" to start the session with the access token and refresh token.
        Provide the refresh_token, and grant_type = "refresh_token" to update the session with the new access token.
    
    Args:
        grant_type (str): The grant type for the token request
        code (str): The authorization code
        refresh_token (str): The refresh token

    Returns:
        redirect: Redirects to the /tracks route
    """
    req_body = {
            'code': code,
            'grant_type': grant_type,
            'refresh_token': refresh_token,
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

    response = requests.post(TOKEN_URL, data=req_body)
    token_info = response.json()
    # If the refresh token is not provided, update the session with the access token
    if refresh_token is None:
        session['access_token'] = token_info['access_token']
    session['refresh_token'] = token_info['refresh_token']
    # Calculate the expiration time of the access token
    session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']
    
    return redirect('/tracks')     


def get_user_data(data_url: str = API_BASE_URL + "/tracks"):
    """
        Get the user's saved songs data from the Spotify API
    
    Args:
        data_url (str): The URL for the user's saved songs data API endpoint

    Returns:
        response object: The user's saved songs data
    """
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    response = requests.get(data_url, headers=headers)
    
    if response.status_code == 200:
        playlists = response.json()
        return jsonify(playlists)
    else:
        return jsonify({"error": "Failed to fetch data"})
    

def get_auth():
    """
        Redirects to the Spotify login page to authorize the app

    Returns:
        redirect: Redirects to the Spotify login page    
    """
    # Define the permission scopes for the Spotify API
    scope = 'user-library-read playlist-modify-private playlist-modify-public'

    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True 
    }

    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)

def get_top_songs():
    """
        Get the user's top songs from the Spotify API up to the SONG_LIMIT constant
    
    Returns:
        list: List containing 2-element tuples of the song name and song ID
    """
    top_songs = []
    user_data = get_user_data()

    while len(top_songs) < SONG_LIMIT and user_data:
        top_songs.extend(user_data.get_json()['items'])
        user_data = get_user_data(data_url=user_data.get_json().get('next'))
    
    song_ids = [(song['track']['name'], song['track']['id']) for song in top_songs]
    return song_ids

@app.route('/')
def index():
    return "Welcome to the Top Songs Spotify Playlist Generator! <a href='/login'>Login with Spotify</a>"


@app.route('/login')
def login():
    return get_auth()


@app.route('/callback')
def callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})
    
    if 'code' in request.args:
        return get_token(grant_type='authorization_code', code=request.args['code'])


@app.route('/tracks')
def tracks():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')

    return f"Welcome to the tracks section!\nYour top {SONG_LIMIT} songs are: \n\n{[str(song[0]) for song in get_top_songs()]}"
    

@app.route('/refresh_token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return get_token(grant_type='refresh_token', refresh_token=session['refresh_token'])

import os
import requests
import urllib.parse
from datetime import datetime
from flask import Flask, redirect, request, jsonify, session
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
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

@app.route('/')
def index():
    return "Welcome to the Top Songs Spotify Playlist Generator! <a href='/login'>Login with Spotify</a>"

@app.route('/login')
def login():
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
    
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    response = requests.get(API_BASE_URL + "/tracks", headers=headers)
    playlists = response.json()

    return jsonify(playlists)

@app.route('/refresh_token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return get_token(grant_type='refresh_token', refresh_token=session['refresh_token'])

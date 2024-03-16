import os
import requests
import urllib.parse
from datetime import datetime
from flask import Flask, redirect, request, jsonify, session, render_template

# Load environment variables
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

# Spotify API URLs
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1'

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
        redirect: Redirects to the /home route
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
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch data"})
    token_info = response.json()
    # If the refresh token is not provided, update the session with the access token
    if refresh_token is None:
        session['access_token'] = token_info['access_token']
    session['refresh_token'] = token_info['refresh_token']
    # Calculate the expiration time of the access token
    session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']
    
    return redirect('/home/20')     


def get_user_data(data_url: str = API_BASE_URL + "/me/tracks"):
    """
        Get the user's saved songs data from the Spotify API
    
    Args:
        data_url (str): The URL for the user's saved songs data API endpoint

    Returns:
        response object: The user's saved songs data
    """
    headers = generate_headers()
    response = requests.get(data_url, headers=headers)
    
    if response.status_code == 200:
        saved_songs = response.json()
        return jsonify(saved_songs)
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


def get_top_songs_data():
    """
        Get the user's top songs from the Spotify API up to the SONG_LIMIT constant
    
    Returns:
        list: The user's top songs data
    """
    top_songs = []
    user_data = get_user_data()
    top_songs.extend(user_data.get_json()['items'])

    # Get the user's top songs, it goes in multiples of 20
    while len(top_songs) < SONG_LIMIT and user_data.get_json().get('next'):
        user_data = get_user_data(data_url=user_data.get_json().get('next'))
        top_songs.extend(user_data.get_json()['items'])

    return top_songs


def get_top_song_ids():
    """
    Get the user's top song ids up to the SONG_LIMIT constant
    
    Returns:
        list: List containing top song IDs
    """
    top_songs = get_top_songs_data()
    # Define the top cutoff limit (if the user wants more songs than he has saved)
    top_limit = SONG_LIMIT if len(top_songs) >= SONG_LIMIT else len(top_songs)
    song_ids = [(song['track']['id']) for song in top_songs][:top_limit]
    return song_ids


def get_top_song_details():
    """
    Get the user's top song and artist names up to the SONG_LIMIT constant
    
    Returns:
        list: List containing a 2-element tuple with the song and artist name
    """
    top_songs = get_top_songs_data()
    # Define the top cutoff limit (if the user wants more songs than he has saved)
    top_limit = SONG_LIMIT if len(top_songs) >= SONG_LIMIT else len(top_songs)
    song_details = [(song['track']['name'], song['track']['artists'][0]['name']) for song in top_songs][:top_limit]
    return song_details


def get_playlist_tracks():
    """
        Get the tracks from the user's playlist.
    
    Returns:
        list: List containing playlist IDs
    """
    playlist_id = find_playlist()
    response = get_user_data(data_url=API_BASE_URL + f"/playlists/{playlist_id}/tracks")

    songs_list = []
    songs_list.extend(response.get_json()['items'])

    while response.get_json()['next']:
        response = get_user_data(data_url=response.get_json().get('next'))
        songs_list.extend(response.get_json()['items'])

    song_ids = [(song['track']['id']) for song in songs_list]
    return song_ids


def check_token_validity(called_by_refresh_route: bool = False):
    """
        Check if the access token is still valid. If not, redirect to the refresh token route. 
        If coming from the refresh token route, return the new access token.
    
    Returns 2 possible responses depending on the route the function is called from:
        redirect: Redirects to the refresh token route 
        response: Returns the new access token
    """
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        if called_by_refresh_route:
            return get_token(grant_type='refresh_token', refresh_token=session['refresh_token'])
        return redirect('/refresh_token')
    
    return session['access_token']


def find_playlist():
    """
        Find the playlist created by the app in a file created in the working directory, matching the SONG_LIMIT constant.
    
    Returns:
        str: The playlist ID or None if the playlist is not found
    """
    try:
        with open('playlist_data.txt', 'r+') as f:
            playlist_data = f.readlines()
            if playlist_data:
                for line in playlist_data:
                    playlist_id, song_count = line.split(',')
                    if int(song_count) == SONG_LIMIT:
                        return playlist_id
    except FileNotFoundError:
        pass
    return None
    

def generate_headers():
    return {'Authorization': f"Bearer {session['access_token']}"}

def chunks(lst):
    """
    Yield successive n-sized chunks from lst. 

    Args:
        lst (list): The list to be split into chunks

    Yields:
        list: A list containing n-sized chunks of the original list
    """
    for i in range(0, len(lst), 100):
        yield lst[i:i + 100]


def create():
    """
        Create a playlist with the user's top songs and save the playlist ID, song number to a file in the working directory

    Returns:
        str: A message indicating whether the playlist was created successfully or if it already exists
    """
    headers = generate_headers()
    playlist_id = find_playlist()
    if playlist_id:
        try:
            requests.put(f"{API_BASE_URL}/playlists/{playlist_id}/followers", headers=headers)
        except:
            pass
        return f"You have already created a playlist with your top {SONG_LIMIT} songs. The playlist ID is: {playlist_id}.<br>"
    with open('playlist_data.txt', 'a') as f:
        playlist_name = f"Top {SONG_LIMIT} Songs"
        response = requests.post(f"{API_BASE_URL}/me/playlists", headers=headers, json={"name": playlist_name, "public": False})
        new_playlist_id = response.json()['id']
        f.write(f"{new_playlist_id},{SONG_LIMIT}\n")
    return f"Playlist created successfully! The playlist ID is: {new_playlist_id}.<br>"


def update():
    """
        Update the playlist corresponding to the song number with the user's top songs
        
    Returns:
        str: A message indicating whether the playlist was updated successfully or if it does not exist
    """
    playlist_id = find_playlist()
    if playlist_id:
        headers = generate_headers()
        # Split the playlist into chunks of 100 and then clear the playlist
        # (You can only add/remove 100 songs at a time from a playlist in Spotify) 
        playlist_song_ids = get_playlist_tracks()
        for chunk in chunks(playlist_song_ids):
            response = requests.delete(f"{API_BASE_URL}/playlists/{playlist_id}/tracks", headers=headers, json={"tracks": [{"uri": f"spotify:track:{song}"} for song in chunk]})
        # Add the user's top songs to the playlist
        top_song_ids = get_top_song_ids()
        # Split the song IDs into chunks of 100 
        for chunk in chunks(top_song_ids):
            response = requests.post(f"{API_BASE_URL}/playlists/{playlist_id}/tracks", headers=headers, json={"uris": [f"spotify:track:{song}" for song in chunk]})
        if response.status_code in [200, 201]:
            return f"Playlist updated successfully! The playlist ID is: {playlist_id}.<br>"
        return f"Failed to update the playlist. The playlist ID is: {playlist_id}.<br>"
    return "No playlist found. Please create a playlist first.<br>"


def delete():
    """
        Delete the playlist corresponding to the song number

    Returns:
        str: A message indicating whether the playlist was deleted successfully or if it does not exist
    """
    playlist_id = find_playlist()
    if playlist_id:
        headers = generate_headers()
        # There is not delete method for playlists in the Spotify API, so we have to unfollow the playlist
        response = requests.delete(f"{API_BASE_URL}/playlists/{playlist_id}/followers", headers=headers)
        if response.status_code == 200:
            return "Playlist deleted successfully!.<br>"
        return response.json()
    return "No playlist found. Please create a playlist first.<br>"


def return_home():
    """
        Return to the home page

    Returns:
        str: A link to the home page
    """
    return f"<a href='/home/{SONG_LIMIT}'>Back to home page</a><br>"


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


@app.route('/home/<songs_requested>')
def home(songs_requested: int = 20):
    global SONG_LIMIT
    SONG_LIMIT = int(songs_requested)
    check_token_validity()
    return f"""<h2>Welcome to the home section!</h2>
            Edit the number in the website address and reload the site to choose how many songs you want in the playlist!<br><br>
            <a href='/create_playlist'>Create a playlist</a><br>
            <a href='/update_playlist'>Update a playlist</a><br>
            <a href='/delete_playlist'>Delete a playlist</a><br><br>
            Your top {SONG_LIMIT} songs are: <br><br>{'<br>'.join('{} by {}'.format(song[0], song[1]) for song in get_top_song_details())}"""
    

@app.route('/refresh_token')
def refresh_token():
    return check_token_validity(called_by_refresh_route=True)


@app.route('/create_playlist')
def create_playlist():
    check_token_validity()
    return create() + update() + return_home()


@app.route('/update_playlist')
def update_playlist():
    check_token_validity()
    return update() + return_home()


@app.route('/delete_playlist')
def delete_playlist():
    check_token_validity()
    return delete() + return_home()
        
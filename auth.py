from app import app
from db import db, users, playlists
import os
import requests
import urllib.parse
from datetime import datetime
from flask import redirect, request, jsonify, session, render_template, url_for

# TO DO:
# - Fix the check_token_validity function, redirects don't work, because the function isn't being returned from the routes
# - Make it so a user can't go into other routes without a valid access token
# - Add some CSS to make the app look better

# Load environment variables
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

# Spotify API URLs
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1'

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
    return redirect(url_for('home', songs_requested=20)) 


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
    if 'SONG_LIMIT' not in session:
        session['SONG_LIMIT'] = 20

    top_songs = []
    user_data = get_user_data()
    top_songs.extend(user_data.get_json()['items'])

    # Get the user's top songs, it goes in multiples of 20
    while len(top_songs) < session['SONG_LIMIT'] and user_data.get_json().get('next'):
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
    top_limit = session['SONG_LIMIT'] if len(top_songs) >= session['SONG_LIMIT'] else len(top_songs)
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
    top_limit = session['SONG_LIMIT'] if len(top_songs) >= session['SONG_LIMIT'] else len(top_songs)
    song_names = [song['track']['name'] for song in top_songs]
    artist_names = [', '.join(artist['name'] for artist in song['track']['artists']) for song in top_songs]
    return zip(song_names[:top_limit], artist_names[:top_limit])


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


def get_user_details():
    """
        Get the user's ID and name from the Spotify API
    
    Returns:
        str: The user's ID and name
    """
    headers = generate_headers()
    response = requests.get(f"{API_BASE_URL}/me", headers=headers)
    return response.json()['id'], response.json()['display_name']


def check_token_validity(called_by_refresh_route: bool = False):
    """
        Check if the access token is still valid. If not, redirect to the refresh token route. 
        If coming from the refresh token route, return the new access token.
    
    Returns 2 possible responses depending on the route the function is called from:
        redirect: Redirects to the refresh token route 
        response: Returns the new access token
    """
    # not currently working
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
    if 'SONG_LIMIT' not in session:
        session['SONG_LIMIT'] = 20
    found_playlist = playlists.query.filter_by(spotify_id=session["user_id"], song_count=session['SONG_LIMIT']).first()
    if found_playlist:
        return found_playlist.playlist_id
    else:
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
        str: The playlist ID
    """
    if 'SONG_LIMIT' not in session:
        session['SONG_LIMIT'] = 20
    headers = generate_headers()
    playlist_id = find_playlist()
    if playlist_id:
        try:
            requests.put(f"{API_BASE_URL}/playlists/{playlist_id}/followers", headers=headers)
        except:
            pass
        return f"You have already created a playlist with your top {session['SONG_LIMIT']} songs.", playlist_id
    playlist_name = f"Top {session['SONG_LIMIT']} Songs"
    response = requests.post(f"{API_BASE_URL}/me/playlists", headers=headers, json={"name": playlist_name, "public": False})
    if response.status_code in [200,201]:
        new_playlist_id = response.json()['id']
        new_playlist = playlists(spotify_id=session["user_id"], playlist_id=new_playlist_id, song_count=session['SONG_LIMIT'])
        db.session.add(new_playlist)
        db.session.commit()
        return f"Playlist created successfully!", new_playlist_id
    return f"Failed to create the playlist.", None


def update():
    """
        Update the playlist corresponding to the song number with the user's top songs
        
    Returns:
        str: A message indicating whether the playlist was updated successfully or if it does not exist
        str: The playlist ID or None if the playlist is not found
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
            return f"Playlist updated successfully!", playlist_id
        return f"Failed to update the playlist.", playlist_id
    return "No playlist found.", None


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
            return "Playlist deleted successfully!."
        return response.json()
    return "No playlist found. Please create a playlist first."


@app.route('/')
def index():
    return render_template('login.html')


@app.route('/login')
def login():
    return get_auth()


@app.route('/callback')
def callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})
    
    if 'code' in request.args:
        return get_token(grant_type='authorization_code', code=request.args['code'])


@app.route('/home', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        session['SONG_LIMIT'] = int(request.form['SONG_LIMIT'])
    check_token_validity()
    user_id = get_user_details()[0]
    found_user = users.query.filter_by(spotify_id=user_id).first()
    if found_user:
        session["user_id"] = found_user.spotify_id
        user_name = found_user.name
    else:
        new_user = users(spotify_id = user_id, name=get_user_details()[1])
        db.session.add(new_user)
        db.session.commit()
        user_name = new_user.name
    return render_template('home.html', song_list = get_top_song_details(), SONG_LIMIT=session['SONG_LIMIT'], user_name=user_name)
    

@app.route('/refresh_token')
def refresh_token():
    return check_token_validity(called_by_refresh_route=True)


@app.route('/create_playlist')
def create_playlist():
    check_token_validity()
    return render_template('feedback.html', feedback=[create()[0], update()[0]], playlist_id=create()[1])


@app.route('/update_playlist')
def update_playlist():
    check_token_validity()
    return render_template('feedback.html', feedback=[update()[0]], playlist_id=update()[1])


@app.route('/delete_playlist')
def delete_playlist():
    check_token_validity()
    return render_template('feedback.html', feedback=[delete()])
        
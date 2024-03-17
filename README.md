# spotify-top-playlist-creator
 App that creates and updates a new playlist on your Spotify account, consisting of top "X" most recent songs in your "Liked" playlist. I made this app to get familiar with Flask, SQLAlchemy and to get some practice working with APIs. The appearance of the site was done using Bootstrap.

 # Usage
 1. Clone this repository to local.
 2. Get your client credentials from the Spotify Web Api website and put them in a ".env" file in the same directory as the code. They should be structured as such:
![alt text](assets/env_keys.png)
 3. Run main.py and follow the REDIRECT_URI you made earlier.
 4. Login with Spotify and authorize.
 5. Choose how many songs you want in the playlist and submit. From there you can create, update or delete the playlist.

 # Examples
 Login page.
![alt text](assets/login.png)
 Home page with chosen songs (do not judge).
![alt text](assets/home.png)
 Create playlist page.
![alt text](assets/create.png)
 Result playlist on Spotify.
![alt text](assets/spotify_result.png)

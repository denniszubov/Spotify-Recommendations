from flask import Flask, request, url_for, render_template, redirect, request, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import secrets
import env
import time


app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_urlsafe(16)
app.config['SESSION_COOKIE_NAME'] = "Spotify Session Cookie"



@app.route('/', methods=['GET'])
def home():
    return render_template("index.html")


@app.route('/dashboard', methods=['GET'])
def dashboard():

    if not authorized():
        return redirect('/')

    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    results = sp.current_user_saved_tracks()
    tracks = []
    for idx, item in enumerate(results['items']):
        track_item = item['track']
        track = {
            "artist": track_item["artists"][0]["name"],
            "track_name": track_item["name"]
        }
        tracks.append(track)

    data = {
        "saved_tracks": tracks
    }
    return render_template("dashboard.html", data=data)


@app.route('/login')
def login():
    sp_oath = create_spotify_oauth()
    auth_url = sp_oath.get_authorize_url()
    return redirect(auth_url)


@app.route('/logout')
def logout():
    for key in list(session.keys()):
        session.pop(key)
    return redirect('/')


@app.route('/callback')
def callback():
    sp_oath = create_spotify_oauth()
    session.clear()
    code = request.args.get("code")
    token_info = sp_oath.get_access_token(code)
    session["token_info"] = token_info

    return redirect(url_for('dashboard'))


# Checks to see if token is valid and gets a new token if not
def get_token():
    token_valid = False
    token_info = session.get("token_info", {})

    # Checking if the session already has a token stored
    if not (session.get('token_info', False)):
        token_valid = False
        return token_info, token_valid

    # Checking if token has expired
    now = int(time.time())
    is_token_expired = session.get('token_info').get('expires_at') - now < 60

    # Refreshing token if it has expired
    if (is_token_expired):
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(session.get('token_info').get('refresh_token'))

    token_valid = True
    return token_info, token_valid


def create_spotify_oauth():
    return SpotifyOAuth(
            client_id= env.CLIENT_ID,
            client_secret= env.CLIENT_SECRET,
            redirect_uri=url_for('callback', _external=True),
            scope="user-library-read")


def authorized():
    session['token_info'], authorized = get_token()
    print(session['token_info'], authorized)
    session.modified = True

    # Redirect is user not logged in
    if not authorized:
        return False
    return True


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)

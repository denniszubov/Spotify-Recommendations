from flask import Flask, request, url_for, render_template, redirect, request, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import secrets
import env
import time
import boto3


app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_urlsafe(16)
app.config['SESSION_COOKIE_NAME'] = "Spotify Session Cookie"


@app.route('/', methods=['GET'])
def home():
    return render_template("index.html")


@app.route('/dashboard', methods=['GET'])
def dashboard():
    dynamodb = boto3.resource('dynamodb', aws_access_key_id = env.AWS_ACCESS_KEY, aws_secret_access_key = env.AWS_SECRET_ACCESS_KEY, region_name = env.AWS_REGION)
    table = dynamodb.Table(env.DYNAMODB_TABLE)
    if not authorized():
        return redirect('/')

    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))

    results = sp.current_user_saved_tracks()
    top_artists = sp.current_user_top_artists(time_range="short_term", limit=5)
    top_artist_ids = [x["id"] for x in top_artists["items"]]
    print("--------------------Top Artists--------------------")
    print(top_artists)
    print(top_artist_ids)
    print()
    recs_based_on_artists = sp.recommendations(limit=10, seed_artists=top_artist_ids)
    rec_tracks = []
    for idx, track_item in enumerate(recs_based_on_artists['tracks']):
        track = {
            "artist": track_item["artists"][0]["name"],
            "track_name": track_item["name"]
        }
        rec_tracks.append(track)

    tracks = []
    for idx, item in enumerate(results['items']):
        track_item = item['track']
        track = {
            "artist": track_item["artists"][0]["name"],
            "track_name": track_item["name"]
        }

        table.put_item(
                Item={
                    "playlist-id": "1",
                    "artist": track_item["artists"][0]["name"],
                    "song-id": track_item["name"]
                }
            )
        
        tracks.append(track)

        
    
    
    data = {
        "saved_tracks": tracks,
        "rec_tracks": rec_tracks
    }
    return render_template("dashboard.html", data=data)


def get_items():
    return dynamodb.scan(
        TableName=env.DYNAMODB_TABLE
    )

@app.route('/getRecs', methods=['GET'])
def getRecs():
    if not authorized():
        return redirect('/')

    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    genre_seeds = sp.recommendation_genre_seeds()["genres"]
    top_tracks = sp.current_user_top_tracks(time_range="short_term", limit=5)
    top_tracks_ids = [x["id"] for x in top_tracks["items"]]
    recs_based_on_tracks = sp.recommendations(seed_tracks = top_tracks_ids, limit=10)
    
    rec_tracks = []
    for idx, track_item in enumerate(recs_based_on_tracks['tracks']):
        track = {
            "artist": track_item["artists"][0]["name"],
            "track_name": track_item["name"]
        }
        rec_tracks.append(track)
        
    data = {
        "rec_tracks": rec_tracks
    }
    return render_template("recsBytrack.html", data=data) 

   
  
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

from flask import Flask, request, url_for, render_template, redirect, request, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import secrets
import env
import time
import boto3
import datetime
from boto3.dynamodb.conditions import Key, Attr


app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_urlsafe(16)
app.config['SESSION_COOKIE_NAME'] = "Spotify Session Cookie"


dynamodb = boto3.resource('dynamodb', aws_access_key_id = env.AWS_ACCESS_KEY, aws_secret_access_key = env.AWS_SECRET_ACCESS_KEY, region_name = env.AWS_REGION)
table = dynamodb.Table(env.DYNAMODB_TABLE)


@app.route('/', methods=['GET'])
def home():
    return render_template("index.html")


@app.route('/home', methods=['GET'])
def dashboard():
    if not authorized():
        return redirect('/')

    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
    session["user_id"] = sp.current_user()["id"]

    # Get Recommendations based on Top Artists
    top_artists = sp.current_user_top_artists(time_range="short_term", limit=5)
    top_artist_ids = [x["id"] for x in top_artists["items"]]

    recs_based_on_artists = sp.recommendations(limit=10, seed_artists=top_artist_ids)
    recs_artists = []
    artist_ids = []
    artist_uris = []
    artist_songArtists = []
    artist_songNames = []

    for idx, track_item in enumerate(recs_based_on_artists['tracks']):
        track = {
            "artist": track_item["artists"][0]["name"],
            "track_name": track_item["name"]
        }
        artist_ids.append(track_item["id"])
        artist_uris.append(track_item["uri"])
        artist_songArtists.append(track_item["artists"][0]["name"])
        artist_songNames.append(track_item["name"])
        recs_artists.append(track)
        

    # Save ids in session storage in case user saves this playlist
    session["artist_ids"] = artist_ids
    session["artist_uris"] = artist_uris
    session["artist_songArtists"] = artist_songArtists
    session["artist_songNames"] = artist_songNames


    # Get Recommendations based on Top Tracks
    top_tracks = sp.current_user_top_tracks(time_range="short_term", limit=5)
    top_tracks_ids = [x["id"] for x in top_tracks["items"]]
    recs_based_on_tracks = sp.recommendations(seed_tracks=top_tracks_ids, limit=10)

    recs_tracks = []
    track_ids = []
    track_uris = []
    track_songArtists = []
    track_songNames = []
    for idx, track_item in enumerate(recs_based_on_tracks['tracks']):
        track = {
            "artist": track_item["artists"][0]["name"],
            "track_name": track_item["name"]
        }
        track_ids.append(track_item["id"])
        track_uris.append(track_item["uri"])
        track_songArtists.append(track_item["artists"][0]["name"])
        track_songNames.append(track_item["name"])
        recs_tracks.append(track)

    # Save ids in session storage in case user saves this playlist
    session["track_ids"] = track_ids
    session["track_uris"] = track_uris
    session["track_songArtists"] = track_songArtists
    session["track_songNames"] = track_songNames

    # General Recommendations
    recs_based_on_both = sp.recommendations(seed_tracks=top_tracks_ids[:3], seed_artists=top_artist_ids[:2], limit=10)
    recs_general = []
    general_ids = []
    general_uris = []
    general_songArtists = []
    general_songNames = []
    for idx, track_item in enumerate(recs_based_on_both['tracks']):
        track = {
            "artist": track_item["artists"][0]["name"],
            "track_name": track_item["name"]
        }
        general_ids.append(track_item["id"])
        general_uris.append(track_item["uri"])
        general_songArtists.append(track_item["artists"][0]["name"])
        general_songNames.append(track_item["name"])
        recs_general.append(track)

    # Save ids in session storage in case user saves this playlist
    session["general_ids"] = general_ids
    session["general_uris"] = general_uris
    session["general_songArtists"] = general_songArtists
    session["general_songNames"] = general_songNames

    data = {
        "recs_artists": recs_artists,
        "recs_tracks": recs_tracks,
        "recs_general": recs_general
    }
    session["data"] = data

    return render_template("dashboard.html", data=data)

@app.route('/getRecs', methods=['GET'])
def getRecs():
    if not authorized():
        return redirect('/')

    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))

    top_tracks = sp.current_user_top_tracks(time_range="short_term", limit=5)
    top_tracks_ids = [x["id"] for x in top_tracks["items"]]
    recs_based_on_tracks = sp.recommendations(seed_tracks=top_tracks_ids, limit=10)
    
    recs_tracks = []
    for idx, track_item in enumerate(recs_based_on_tracks['tracks']):
        track = {
            "artist": track_item["artists"][0]["name"],
            "track_name": track_item["name"]
        }
        recs_tracks.append(track)
        
    data = {
        "recs_tracks": recs_tracks
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


@app.route('/saved-playlists', methods=['GET'])
def saved():
    if not authorized():
        return redirect('/')

    user_id = session.get("user_id")
    # Send to login if the user id is not in the session
    if not user_id:
        return redirect('/')
    response = table.scan(FilterExpression=Attr('user').eq(user_id)).get("Items")
    # print(response)
    playlists = []
    for pl in response:
        track_names = pl["song-names"].split(",")
        # print(track_names)
        track_artists = pl["song-artists"].split(",")
        # print(track_artists)
        playlist = {
            "tracks": [],
            "id": pl["playlist-id"]
        }
        for name, artist in zip(track_names, track_artists):
            playlist["tracks"].append(
                {
                    "name": name,
                    "artist": artist
                }
            )
        playlists.append(playlist)
        
    # print(playlists)
    return render_template("saved-playlists.html", data={"playlists": playlists})


@app.route('/save-general-playlist', methods=['GET'])
def save_general_playlist():
    if not authorized():
        return redirect('/')

    user_id = session.get("user_id")
    # Send to login if the user id is not in the session
    if not user_id:
        return redirect('/')

    # Save this playlist to dynamo db
    general_ids = session.get("general_ids")
    general_uris = session.get("general_uris")
    general_songArtists = session.get("general_songArtists")
    general_songNames = session.get("general_songNames")
    song_ids = ",".join(general_ids)
    song_uris = ",".join(general_uris)
    song_artists = ",".join(general_songArtists)
    song_names = ",".join(general_songNames)

    table.put_item(
        Item={
            "playlist-id": "G" + str(int(datetime.datetime.now().strftime('%s'))),
            "song-id": song_ids,
            "song-uris": song_uris,
            "user": user_id,
            "song-artists": song_artists,
            "song-names": song_names
        }
    )

    return render_template("dashboard.html", data=session.get("data"))


@app.route('/save-tracks-playlist', methods=['GET'])
def save_tracks_playlist():
    if not authorized():
        return redirect('/')

    user_id = session.get("user_id")
    # Send to login if the user id is not in the session
    if not user_id:
        return redirect('/')

    # Save this playlist to dynamo db
    track_ids = session.get("track_ids")
    track_uris = session.get("track_uris")
    track_songArtists = session.get("track_songArtists")
    track_songNames = session.get("track_songNames")
    song_ids = ",".join(track_ids)
    song_uris = ",".join(track_uris)
    song_artists = ",".join(track_songArtists)
    song_names = ",".join(track_songNames)

    table.put_item(
        Item={
            "playlist-id": "T" + str(int(datetime.datetime.now().strftime('%s'))),
            "song-id": song_ids,
            "song-uris": song_uris,
            "user": user_id,
            "song-artists": song_artists,
            "song-names": song_names
        }
    )

    return render_template("dashboard.html", data=session.get("data"))


@app.route('/save-artists-playlist', methods=['GET'])
def save_artists_playlist():
    if not authorized():
        return redirect('/')

    user_id = session.get("user_id")
    # Send to login if the user id is not in the session
    if not user_id:
        return redirect('/')

    # Save this playlist to dynamo db
    artist_ids = session.get("artist_ids")
    artist_uris = session.get("artist_uris")
    artist_songArtists = session.get("artist_songArtists")
    artist_songNames = session.get("artist_songNames")
    song_ids = ",".join(artist_ids)
    song_uris = ",".join(artist_uris)
    song_artists = ",".join(artist_songArtists)
    song_names = ",".join(artist_songNames)

    table.put_item(
        Item={
            "playlist-id": "A" + str(int(datetime.datetime.now().strftime('%s'))),
            "song-id": song_ids,
            "song-uris": song_uris,
            "user": user_id,
            "song-artists": song_artists,
            "song-names": song_names
        }
    )

    return render_template("dashboard.html", data=session.get("data"))


# Delete all saved playlists
@app.route('/delete-saved-playlists', methods=["GET"])
def delete_saved_playlists():
    if not authorized():
        return redirect('/')

    user_id = session.get("user_id")
    # Send to login if the user id is not in the session
    if not user_id:
        return redirect('/')

    response = table.scan(FilterExpression=Attr('user').eq(user_id)).get("Items")
    for item in response:
        table.delete_item(
            Key={
                "playlist-id": item["playlist-id"],
                "song-id": item["song-id"]
            }
        )

    return render_template("saved-playlists.html", data=session.get("data"))


@app.route('/about', methods=['GET'])
def about():
    if not authorized():
        return redirect('/')

    return render_template("about.html")


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
            client_id=env.CLIENT_ID,
            client_secret=env.CLIENT_SECRET,
            redirect_uri=url_for('callback', _external=True),
            scope="user-library-read user-library-modify playlist-modify-private playlist-modify-public user-read-recently-played user-top-read")


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

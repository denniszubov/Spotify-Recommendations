from flask import Flask, request, url_for, render_template, redirect, request
import startup


# Client ID: 502e4c3cf6144515957f46ada1a95bee
# Client Secret: ca2e4badc0034cd2925a10f10fb26c96
# Redirect URI: http://localhost:5000/callback/


app = Flask(__name__)


@app.route('/', methods=['GET'])
def home_page():
    return render_template("index.html")


@app.route('/dashboard/', methods=['GET'])
def dashboard():
    return render_template("dashboard.html")


@app.route('/auth/')
def index():
    response = startup.getUser()
    return redirect(response)


@app.route('/callback/')
def callback():
    startup.getUserToken(request.args['code'])
    return redirect('/dashboard/')


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)

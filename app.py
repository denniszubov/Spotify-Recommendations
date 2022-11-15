from flask import Flask, request, url_for, render_template, redirect, request
import startup


app = Flask(__name__)


@app.route('/', methods=['GET'])
def home_page():
    return render_template("index.html")


@app.route('/auth/')
def index():
    response = startup.getUser()
    return redirect(response)

@app.route('/callback/')
def callback():
    startup.getUserToken(request.args['code'])
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)

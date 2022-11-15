from flask import Flask, request, url_for, render_template, redirect, request


app = Flask(__name__)


@app.route('/', methods=['GET'])
def home_page():
    return render_template("index.html")


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)

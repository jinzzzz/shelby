from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os, base64, hashlib
from openai import OpenAI
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite3"

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

# 🧑 User table
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))

# 🖼️ Image table
class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.String(200))
    filename = db.Column(db.String(200))
    user_id = db.Column(db.Integer)
    time = db.Column(db.String(100))
    hash = db.Column(db.String(200))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 🏠 Home
@app.route("/")
@login_required
def home():
    search = request.args.get("search", "")
    if search:
        images = Image.query.filter(Image.prompt.contains(search)).all()
    else:
        images = Image.query.all()
    return render_template("index.html", images=images)

# 🔐 Register
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        user = User(username=request.form["username"], password=request.form["password"])
        db.session.add(user)
        db.session.commit()
        return redirect("/login")
    return render_template("register.html")

# 🔐 Login
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"], password=request.form["password"]).first()
        if user:
            login_user(user)
            return redirect("/")
    return render_template("login.html")

@app.route("/logout")
def logout():
    logout_user()
    return redirect("/login")

# 🎨 Generate AI image
@app.route("/generate", methods=["POST"])
@login_required
def generate():
    prompt = request.form["prompt"]

    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )

    img = base64.b64decode(result.data[0].b64_json)

    filename = prompt.replace(" ", "_") + ".png"
    path = os.path.join("static", filename)

    with open(path, "wb") as f:
        f.write(img)

    hash_value = hashlib.sha256(prompt.encode()).hexdigest()

    image = Image(
        prompt=prompt,
        filename=filename,
        user_id=current_user.id,
        time=datetime.now().strftime("%H:%M %d-%m-%Y"),
        hash=hash_value
    )

    db.session.add(image)
    db.session.commit()

    return redirect("/")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
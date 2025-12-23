from flask import Flask, render_template

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    # on branche l'API
    from src.app.api import api_bp
    app.register_blueprint(api_bp)

    return app

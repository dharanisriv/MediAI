"""
MediAI - entry point.

  Local:    python app.py            -> open http://127.0.0.1:5000
  Hosting:  gunicorn app:app         (see the Dockerfile)
  Colab:    see MediAI_Colab.ipynb   (it imports `create_app` from the backend package)
"""
import os

from backend import create_app

# `app` is the Flask application object that gunicorn / Colab / python use.
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    # 127.0.0.1 = only your own computer can open the site (safe default).
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=port, debug=debug)

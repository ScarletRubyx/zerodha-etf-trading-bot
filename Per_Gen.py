# ============================================================
# Per_Gen.py — Zerodha Kite OAuth login via local Flask callback.
# Flask server shuts down automatically after token is received.
# ============================================================

from flask import Flask, request
from kiteconnect import KiteConnect
import threading
import config
import webbrowser

app = Flask(__name__)

# Shared state between Flask thread and main thread
request_token = None
token_received = threading.Event()
_server = None  # Reference to the werkzeug server for shutdown


@app.route("/")
def callback():
    global request_token

    request_token = request.args.get("request_token")

    if request_token:
        token_received.set()
        # Schedule server shutdown after response is sent
        threading.Thread(target=_shutdown_server).start()
        return "Login Successful! You may close this window."

    return "No request token received."


def _shutdown_server():
    """Stop the Flask/werkzeug server from a background thread."""
    import time
    time.sleep(0.5)  # Brief pause so Flask can finish sending the response
    if _server:
        _server.shutdown()


def run_flask():
    """Run Flask using werkzeug's make_server so we can shut it down."""
    global _server
    from werkzeug.serving import make_server
    _server = make_server("127.0.0.1", 5000, app)
    _server.serve_forever()


def login() -> KiteConnect:
    """
    Opens Zerodha login in browser, waits for OAuth callback,
    generates session, and returns an authenticated KiteConnect instance.
    Flask server shuts itself down once the token is received.
    """
    # Start Flask server in a background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    kite = KiteConnect(api_key=config.API_KEY)

    # Open Zerodha login in default browser
    webbrowser.open(kite.login_url())

    print("Waiting for Zerodha login...")

    # Block until callback() sets the event
    token_received.wait()

    print("Request token received! Generating session...")

    data = kite.generate_session(
        request_token,
        api_secret=config.API_SECRET,
    )

    kite.set_access_token(data["access_token"])
    print(f"Logged in successfully. Access token set.")

    return kite

from flask import Flask, redirect, url_for, session, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import requests
from msal import ConfidentialClientApplication

# Flask app setup
app = Flask(__name__)
app.secret_key = "your_secret_key"

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Azure AD Configuration
TENANT_ID = "your_tenant_id"
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/.default"]
REDIRECT_URI = "http://localhost:5000/getAToken"

# Group ID to check
REQUIRED_GROUP_ID = "your_group_id"

# MSAL client
msal_app = ConfidentialClientApplication(CLIENT_ID, CLIENT_SECRET, AUTHORITY)


# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id, name, email):
        self.id = user_id
        self.name = name
        self.email = email


# User loader function
@login_manager.user_loader
def load_user(user_id):
    return session.get("user")


@app.route("/login")
def login():
    """Redirects user to Microsoft's login page."""
    auth_url = msal_app.get_authorization_request_url(SCOPES, redirect_uri=REDIRECT_URI)
    return redirect(auth_url)


@app.route("/getAToken")
def get_token():
    """Handles Azure AD OAuth callback."""
    code = request.args.get("code")
    if not code:
        return "Authorization failed", 400

    token_response = msal_app.acquire_token_by_authorization_code(code, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    
    if "access_token" not in token_response:
        return "Failed to obtain token", 400

    access_token = token_response["access_token"]

    # Get user info
    user_data = requests.get("https://graph.microsoft.com/v1.0/me", headers={"Authorization": f"Bearer {access_token}"}).json()
    user_id = user_data["id"]
    user_email = user_data["mail"] or user_data["userPrincipalName"]
    user_name = user_data["displayName"]

    # Check group membership
    group_data = requests.get(f"https://graph.microsoft.com/v1.0/users/{user_id}/memberOf",
                              headers={"Authorization": f"Bearer {access_token}"}).json()

    group_ids = {group["id"] for group in group_data.get("value", [])}
    
    if REQUIRED_GROUP_ID not in group_ids:
        return "Unauthorized", 403

    # Create user session
    user = User(user_id, user_name, user_email)
    session["user"] = user
    login_user(user)

    return redirect(url_for("protected"))


@app.route("/logout")
@login_required
def logout():
    """Logs out the user."""
    logout_user()
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/protected")
@login_required
def protected():
    """Protected route only accessible to logged-in users."""
    return f"Hello, {session['user'].name}! You have access."


if __name__ == "__main__":
    app.run(debug=True)

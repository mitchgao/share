from flask import Flask, redirect, url_for, session, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import dash
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import requests
from msal import ConfidentialClientApplication

# Flask setup
server = Flask(__name__)
server.secret_key = "your_secret_key"

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = "/login"

# Azure AD Configuration
TENANT_ID = "your_tenant_id"
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/.default"]
REDIRECT_URI = "http://localhost:5000/getAToken"

# Required Azure AD Group ID
REQUIRED_GROUP_ID = "your_group_id"

# MSAL client
msal_app = ConfidentialClientApplication(CLIENT_ID, CLIENT_SECRET, AUTHORITY)


# Flask-Login User class
class User(UserMixin):
    def __init__(self, user_id, name, email):
        self.id = user_id
        self.name = name
        self.email = email


# User loader function
@login_manager.user_loader
def load_user(user_id):
    return session.get("user")


@server.route("/login")
def login():
    """Redirect user to Microsoft Login"""
    auth_url = msal_app.get_authorization_request_url(SCOPES, redirect_uri=REDIRECT_URI)
    return redirect(auth_url)


@server.route("/getAToken")
def get_token():
    """Handles Azure AD OAuth callback"""
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

    return redirect("/")


@server.route("/logout")
@login_required
def logout():
    """Logs out the user"""
    logout_user()
    session.pop("user", None)
    return redirect("/")


# Initialize Dash App
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Layout
app.layout = html.Div([
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("Login", href="/login", id="login-link")),
            dbc.NavItem(dbc.NavLink("Logout", href="/logout", id="logout-link", style={"display": "none"})),
        ],
        brand="Dash App with Azure AD Auth",
        color="primary",
        dark=True,
    ),
    html.Div(id="page-content")
])


# Callback to update navbar based on login status
@app.callback(
    Output("login-link", "style"),
    Output("logout-link", "style"),
    Input("page-content", "children")  # Just a dummy trigger
)
def update_navbar(_):
    if current_user.is_authenticated:
        return {"display": "none"}, {"display": "block"}
    return {"display": "block"}, {"display": "none"}


@app.callback(
    Output("page-content", "children"),
    Input("page-content", "children")  # Dummy input for triggering updates
)
def display_page(_):
    if current_user.is_authenticated:
        return html.Div([
            html.H2(f"Welcome, {current_user.name}!"),
            html.P("You are authorized to view this page."),
        ])
    else:
        return html.Div([
            html.H2("Please log in to access the application."),
            html.A("Login", href="/login")
        ])


# Run the server
if __name__ == "__main__":
    app.run(debug=True)




import requests

SPN_ID = "your_spn_id"  # This is the Application (Client) ID
SPN_SECRET = "your_spn_password"  # This is the SPN password
AUTHORITY = "https://login.microsoftonline.com"

# Try to authenticate with Azure AD
token_url = f"{AUTHORITY}/organizations/oauth2/v2.0/token"
data = {
    "grant_type": "client_credentials",
    "client_id": SPN_ID,
    "client_secret": SPN_SECRET,
    "scope": "https://graph.microsoft.com/.default"
}

response = requests.post(token_url, data=data)
if response.status_code == 200:
    tenant_id = response.json().get("token_type", "").split("/")[3]  # Extract Tenant ID
    print("TENANT_ID:", tenant_id)
else:
    print("Failed to retrieve Tenant ID:", response.json())

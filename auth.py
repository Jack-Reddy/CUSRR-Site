from authlib.integrations.flask_client import OAuth
import os

oauth = OAuth()


def init_oauth(app):

    if not getattr(app, 'secret_key', None):
        app.secret_key = os.environ.get('APP_SECRET_KEY')

    oauth.init_app(app)

    oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),

        # API endpoints
        access_token_url='https://accounts.google.com/o/oauth2/token',
        access_token_params=None,

        # metadata (use Google's OpenID Connect discovery so Authlib can retrieve jwks_uri and other metadata required for OIDC)
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',

        # login page
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        authorize_params=None,

        api_base_url='https://www.googleapis.com/oauth2/v1/',
        client_kwargs={'scope': 'openid email profile'},
    )



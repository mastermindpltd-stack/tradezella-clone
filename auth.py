import streamlit_authenticator as stauth

def get_authenticator():

    credentials = {
        "usernames": {
            "vicky": {
                "name": "Vicky",
                "password": stauth.Hasher(["12345"]).generate()[0]
            },
            "test": {
                "name": "Test",
                "password": stauth.Hasher(["test123"]).generate()[0]
            }
        }
    }

    authenticator = stauth.Authenticate(
        credentials,
        "tradezella_cookie",
        "tradezella_key",
        1   # cookie_expiry_days (positional)
    )

    return authenticator

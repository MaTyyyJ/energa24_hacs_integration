import logging
import re
import uuid
import requests
import jwt
from urllib.parse import urlparse, parse_qs
from .utils import generate_pkce_challenge, generate_code_verifier

_LOGGER = logging.getLogger(__name__)

AUTH_URL = "https://24.energa.pl/auth/realms/Energa-Selfcare/protocol/openid-connect/auth"
TOKEN_URL = "https://24.energa.pl/auth/realms/Energa-Selfcare/protocol/openid-connect/token"
BASE_URL = "https://24.energa.pl"
REDIRECT_URI = "https://24.energa.pl/ss/"

class EnergaAuth:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self._session = requests.Session()
        self._token = None
        self._keycloak_id = None

    def login(self):
        """Performs the login flow and returns token_type, access_token, and keycloak_id."""
        verifier = generate_code_verifier(96)
        code_challenge = generate_pkce_challenge("S256", verifier)

        init_url = f'{AUTH_URL}?client_id=energa-selfcare&redirect_uri={REDIRECT_URI}&state={uuid.uuid4()}&response_mode=fragment&response_type=code&scope=openid&nonce={uuid.uuid4()}&code_challenge={code_challenge}&code_challenge_method=S256'

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        }

        response_page = self._session.get(init_url, headers=headers)
        pattern = r'id="oid-button"[^>]*href="([^"]+)"'

        match = re.search(pattern, response_page.text)

        if match:
            raw_url = match.group(1)
            clean_url = BASE_URL + raw_url.replace('&amp;', '&')
            response_page = self._session.get(clean_url, headers=headers)
            match = re.search(r'action="([^"]+)"', response_page.text)
            if match:
                post_url = match.group(1).replace('&amp;', '&')
                payload = {
                    'username': self.username,
                    'password': self.password,
                    'credentialId': ''
                }
                final_response = self._session.post(post_url, data=payload, headers=headers)
                if final_response.status_code == 200:
                    fragment = urlparse(final_response.url).fragment
                    parsed_dict = {k: v[0] for k, v in parse_qs(fragment).items()}
                    if 'code' in parsed_dict:
                        data = {
                            'code': parsed_dict['code'],
                            'grant_type': 'authorization_code',
                            'client_id': 'energa-selfcare',
                            'redirect_uri': REDIRECT_URI,
                            'code_verifier': verifier
                        }
                        headers.update({'Referer': 'https://24.energa.pl/ss/dashboard'})
                        res_auth = self._session.post(TOKEN_URL, headers=headers, data=data)
                        if res_auth.status_code == 200:
                            response = res_auth.json()
                            self._token = response.get('access_token')
                            token_type = response.get('token_type')
                            self._keycloak_id = jwt.decode(self._token, algorithms=['RS256'],
                                                      options={"verify_signature": False})
                            return token_type, self._token, self._keycloak_id
        
        raise Exception("Login failed")

    def get_headers(self):
        if not self._token:
            self.login()
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'Authorization': f"Bearer {self._token}",
            'Content-Type': 'application/json',
        }
    
    def get_keycloak_id(self):
        if not self._keycloak_id:
            self.login()
        return self._keycloak_id

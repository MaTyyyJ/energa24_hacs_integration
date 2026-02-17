import hashlib
import base64
import secrets
import string

def generate_pkce_challenge(pkce_method, code_verifier):
    if pkce_method != "S256":
        raise TypeError(f"Invalid value for 'pkceMethod', expected 'S256' but got '{pkce_method}'.")

    # Hashowanie i kodowanie (SHA256 -> Base64Url)
    digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')


# 2. Funkcja generująca Code Verifier (odpowiednik anonimowej funkcji 'e')
def generate_code_verifier(length=96):
    """
    Generuje kryptograficznie bezpieczny losowy ciąg znaków.
    JS używa: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    """
    charset = string.ascii_letters + string.digits  # To dokładnie ten sam zestaw znaków co w JS

    # Używamy secrets (bezpieczniejsze niż random)
    return ''.join(secrets.choice(charset) for _ in range(length))
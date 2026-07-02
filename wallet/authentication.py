from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate from Authorization header or access_token cookie."""

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
        else:
            raw_token = self.get_raw_token_from_cookie(request)

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token

    def get_raw_token_from_cookie(self, request):
        return request.COOKIES.get('access_token')


class JWTSessionMiddleware:
    """Populate request.user from a JWT access token cookie when no session exists."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.authenticator = CookieJWTAuthentication()

    def __call__(self, request):
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            try:
                auth_result = self.authenticator.authenticate(request)
                if auth_result is not None:
                    user, token = auth_result
                    request.user = user
                    request.auth = token
            except AuthenticationFailed:
                pass

        return self.get_response(request)

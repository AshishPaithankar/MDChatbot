from rest_framework import exceptions
from rest_framework.authentication import get_authorization_header
from authentication.models.AuthToken import AuthToken
from mdchatbot.constants.Delimiters import Delimiters
from mdchatbot.constants.PermittedUrls import PermittedUrls
from authentication.constants.JWTConfiguration import JWTConfigurations
import jwt


class JWTAuthentication:
    """
    To support jwt authentication with Authorization: Token
    """

    def __init__(self):
        self.keyword = "Token"

    @staticmethod
    def get_token(request):
        auth = get_authorization_header(request).split()
        if not (auth and len(auth) == 2 and len(str(auth[1]).split(Delimiters.DOT)) == 3):
            return None
        return auth[1].decode()

    @staticmethod
    def validate_permissions(request, auth_token):
        admin_staff_users = ()
        if request.method != 'GET' and auth_token.staff_user and auth_token.staff_user_id not in admin_staff_users and \
                request.get_full_path().split('/')[-1] not in PermittedUrls.STAFF_LOGIN_AS:
            raise exceptions.PermissionDenied()

    def authenticate(self, request):
        token = self.get_token(request)
        if not token:
            return
        try:
            decoded = jwt.decode(token, JWTConfigurations.SIGNING_KEY, algorithms=[JWTConfigurations.ALGORITHM])
            auth_token = AuthToken.objects.get(user_id=decoded.get("user_id"),
                                               is_active=True,
                                               access_token=token)
            self.validate_permissions(request, auth_token)
            return auth_token.user, None
        except exceptions.PermissionDenied:
            raise exceptions.PermissionDenied("You are not permitted to perform this action.")
        except Exception:
            raise exceptions.AuthenticationFailed("Invalid Token.")

    def authenticate_header(self, request):
        return self.keyword
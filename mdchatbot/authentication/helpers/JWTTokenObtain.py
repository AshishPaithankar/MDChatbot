import jwt
from uuid import uuid4
from datetime import datetime, timezone
from authentication.constants.JWTConfiguration import JWTConfigurations
from authentication.models.AuthToken import AuthToken

class JWTTokenObtain:

    @staticmethod
    def obtain_token(claims, expiry_time):
        claims.update({
            "exp": expiry_time,
        })
        token = jwt.encode(claims, key=JWTConfigurations.SIGNING_KEY, algorithm=JWTConfigurations.ALGORITHM)
        return token

    @staticmethod
    def create_and_get_tokens(request, user, **kwargs):
        access_token_expiry_time = datetime.now(timezone.utc) + JWTConfigurations.ACCESS_TOKEN_LIFETIME
        access_token_jti = uuid4().hex
        access_token = JWTTokenObtain.obtain_token({
            "user_id": user.id,
            "jti": access_token_jti
        }, expiry_time=access_token_expiry_time)
        refresh_token_expiry_time = datetime.now(timezone.utc) + JWTConfigurations.REFRESH_TOKEN_LIFETIME
        refresh_token = JWTTokenObtain.obtain_token({
            "user_id": user.id,
            "jti": uuid4().hex
        }, expiry_time=refresh_token_expiry_time)
        AuthToken.objects.create(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            platform=kwargs.get('platform') or request.GET.get("src"),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            refresh_token_expires_at=refresh_token_expiry_time,
            access_token_expires_at=access_token_expiry_time,
            staff_user_id=kwargs.get('staff_user_id'),
            session_id=kwargs.get('session_id') or access_token_jti,
            session_created_at=kwargs.get('session_created_at') or datetime.now(timezone.utc)
        )
        return access_token, refresh_token
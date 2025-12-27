from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from authentication.helpers.JWTTokenObtain import JWTTokenObtain


class CustomObtainAuthTokenViewSet(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        access_token, refresh_token = JWTTokenObtain.create_and_get_tokens(request, user)
        return Response({
            "token": access_token,
            "refresh_token": refresh_token
        })


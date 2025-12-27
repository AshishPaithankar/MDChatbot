"""
URL configuration for mdchatbot project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from authentication.views import CustomObtainAuthTokenViewSet

urlpatterns = [
    # Django admin panel route (for managing users, models, etc.)
    path("admin/", admin.site.urls),

    # Include all chat-related endpoints from chat/urls.py
    path('api/chat/', include('chat.urls')),

    # Endpoint to obtain authentication token (likely for login)
    path('api/auth_token/', CustomObtainAuthTokenViewSet.as_view(), name='auth_token'),
]

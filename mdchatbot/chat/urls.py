from django.urls import path
from . import views
from .views import ChatAPIView, ConversationHistoryAPIView


urlpatterns = [
    # POST endpoint to send a chat message and receive a response
    path('', views.ChatAPIView.as_view(), name='chat-api'),

    # GET endpoint to fetch past conversation history
    path('history/', ConversationHistoryAPIView.as_view(), name='chat-history'),
]

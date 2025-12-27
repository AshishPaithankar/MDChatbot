from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

class UserProfile(models.Model):
    """
    Stores additional profile information for Django users.
    Used for internal users managing the system.
    """
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)
    first_name = models.CharField(max_length=32, null=True, blank=True)
    last_name = models.CharField(max_length=32, null=True, blank=True)
    mobile = models.CharField(max_length=16, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)  # Set on create
    updated = models.DateTimeField(auto_now=True)      # Set on update
    last_seen = models.DateTimeField(null=True)        # Last activity timestamp

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()


class ClientUser(models.Model):
    """
    Represents a unique user of a specific client system (like MD or ProAMCU).
    """
    user_id = models.IntegerField(unique=True, null=True)  # Unique user ID (external)
    client_id = models.IntegerField(
        choices=[(1, 'MD'), (2, 'ProAMCU')],
        default=1
    )  # Used to identify which client the user belongs to
    name = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.ForeignKey(
        UserProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )  # Optional admin who last updated this
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Client ID: {self.client_id})"


class Conversation(models.Model):
    """
    Tracks each chat session initiated by a client user.
    """
    client_user = models.ForeignKey(ClientUser, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=255, unique=True)  # UUID or unique token for the session
    start_time = models.DateTimeField(default=timezone.now)     # When session began
    last_active = models.DateTimeField(auto_now=True)           # Updated on every interaction

    def __str__(self):
        return f"Session {self.session_id} - {self.client_user.name}"


class ConversationHistory(models.Model):
    """
    Stores a message pair (user + assistant) within a conversation session.
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    user_text = models.TextField(null=True, blank=True)  # Original user message
    assistant_text = models.JSONField(null=True, blank=True)  # Gemini JSON response
    request_at = models.DateTimeField(auto_now_add=True)  # Timestamp when user sent message
    response_at = models.DateTimeField(null=True, blank=True)  # Set when assistant replies

    def save(self, *args, **kwargs):
        """
        Automatically set response_at when assistant_text is added.
        This avoids manual setting in code.
        """
        if self.assistant_text and not self.response_at:
            self.response_at = timezone.now()
        super().save(*args, **kwargs)

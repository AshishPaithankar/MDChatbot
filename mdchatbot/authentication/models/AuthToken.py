from django.db import models, transaction
from authentication.constants.Platforms import Platforms
class AuthToken(models.Model):
    PLATFORM_OPTIONS = (
        (Platforms.AMDC, Platforms.AMDC),
        (Platforms.AMD, Platforms.AMD),
        (Platforms.MDT, Platforms.MDT),
        (Platforms.WEB, Platforms.WEB)
    )
    user = models.ForeignKey('auth.user', related_name='token_user', on_delete=models.CASCADE)
    staff_user = models.ForeignKey('auth.user', blank=True, null=True, on_delete=models.SET_NULL)
    access_token = models.TextField()
    refresh_token = models.TextField()
    access_token_expires_at = models.DateTimeField()
    refresh_token_expires_at = models.DateTimeField()
    session_id = models.CharField(max_length=32)
    session_created_at = models.DateTimeField()
    platform = models.CharField(max_length=8, choices=PLATFORM_OPTIONS, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    user_agent = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Token for {self.user} is {self.access_token}'

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @classmethod
    def deactivate_tokens_for_user(cls, user):
        cls.objects.filter(user=user, is_active=True).update(is_active=False)

    class Meta:
        app_label = 'authentication'
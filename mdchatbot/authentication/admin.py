from django.contrib import admin
from authentication.models.AuthToken import AuthToken

class AuthTokenAdmin(admin.ModelAdmin):
    list_per_page = 10
    list_display = ('id', 'user_id', 'staff_user_id', 'platform', 'is_active', 'session_id',
                    'session_created_at', 'access_token_expires_at',
                    'refresh_token_expires_at', 'created_at', 'updated_at')
    raw_id_fields = ('user', 'staff_user')
    search_fields = ('user_id',)

admin.site.register(AuthToken, AuthTokenAdmin)

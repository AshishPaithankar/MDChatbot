from django.contrib import admin
from .models import UserProfile, ClientUser, Conversation, ConversationHistory 
from .adminform import UserProfileForm
from django.contrib.auth.models import User

class UserProfileAdmin(admin.ModelAdmin):
    search_fields = ['mobile', 'first_name', 'last_name']
    list_display = [field.attname for field in UserProfile._meta.fields]
    form = UserProfileForm

    def save_model(self, request, obj, form, change):
        data = form.clean()
        user, created = User.objects.get_or_create(username=data['mobile'])
        if data.get('first_name'):
            user.first_name = data.get('first_name')
        if data.get('last_name'):
            user.last_name = data.get('last_name')
        if data.get('email'):
            user.email = data.get('email')
        if data.get('password'):
            user.set_password(data.get('password'))
        user.save()
        obj.user = user
        obj.mobile = data['mobile']
        obj.first_name = data['first_name']
        obj.last_name = data['last_name']
        obj.email = data['email']
        obj.is_verified = True
        obj.save()
        return obj


class ClientUserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'name', 'client_id', 'updated', 'updated_by')  # Updated fields
    search_fields = ('user_id', 'name', 'client_id')
    ordering = ('-updated',)  # Using 'updated' instead of 'created_at'


class ConversationAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'client_user', 'start_time', 'last_active')  # Added 'start_time'
    search_fields = ('session_id', 'client_user__name')
    ordering = ('-last_active',)

class ConversationHistoryAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'user_text', 'assistant_text', 'request_at', 'response_at')
    search_fields = ('conversation__session_id', 'user_text', 'assistant_text')
    ordering = ('-request_at',)

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(ClientUser,ClientUserAdmin)
admin.site.register(Conversation,ConversationAdmin)
admin.site.register(ConversationHistory,ConversationHistoryAdmin)



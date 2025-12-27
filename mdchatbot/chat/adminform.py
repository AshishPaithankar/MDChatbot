from django import forms
from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    password = forms.CharField(
        max_length=128, required=False,widget=forms.PasswordInput
    )

    class Meta:
        model = UserProfile
        fields = [
            'first_name' ,
            'last_name' ,
            'mobile',
            'email' ,
            ]


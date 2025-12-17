from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=True)

    class Meta:
        model = User
        fields = ('username','first_name','last_name','email','phone','password1','password2',)
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered")
        return email
class EmailOrUsernameLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={"autofocus": True})
    )

    def clean(self):
        cleaned_data = super().clean()
        username_or_email = cleaned_data.get("username")

        if username_or_email and "@" in username_or_email:
            try:
                user = User.objects.get(email=username_or_email)
                cleaned_data["username"] = user.username
            except User.DoesNotExist:
                pass

        return cleaned_data
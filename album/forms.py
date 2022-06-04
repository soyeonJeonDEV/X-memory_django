
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Photo, PhotoTag


class UserForm(UserCreationForm):
    email = forms.EmailField(label = '이메일')
    User = get_user_model()

    class Meta(UserCreationForm.Meta):
        User = get_user_model()
        model = User
        fields = ('username', 'email')
        

class PhotoForm(forms.ModelForm):
  class Meta:
    model=Photo
    fields=['photo']
    labels = {
    'photo':'사진',
    }

class TagForm(forms.ModelForm):
  class Meta:
    model=PhotoTag
    fields=['photo','tags']
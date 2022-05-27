from django.db import models
from django.conf import settings
# Create your models here.

class Photo(models.Model):
    title = models.CharField(max_length = 200,blank=True,null=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE, related_name='photo_author')
    content = models.TextField(null=True, blank=True)
    photo = models.ImageField(upload_to="pic/",blank=True,null=True)
    create_date = models.DateTimeField()
    modify_date = models.DateTimeField(null=True, blank=True)
    tags=models.CharField(max_length=1000,default='',blank=True)
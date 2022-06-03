from django.db import models
from django.conf import settings
# Create your models here.

class Photo(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE, related_name='photo_author')
    photo = models.ImageField(upload_to="pic/",blank=True,null=True)




# 별점필드, 리뷰 필드
class PhotoTag(models.Model):
    tags = models.CharField(max_length=100, default="",null=True,blank=True)
    create_date = models.DateField()
    latitude  = models.CharField(max_length=100, default="",null=True,blank=True)
    longitude  = models.CharField(max_length=100, default="",null=True,blank=True)
    starScore = models.CharField(max_length=100, default="",null=True,blank=True)
    review = models.CharField(max_length=100, default="",null=True,blank=True)
    photo = models.ForeignKey(Photo, null=False, on_delete=models.CASCADE, related_name='photo_id')


# 분석결과 테이블
# 유저테이블 연결
class analysis(models.Model):
    feild1 = models.CharField(max_length=100, default="",blank=True)
    feild2 = models.CharField(max_length=100, default="",blank=True)
    feild3 = models.CharField(max_length=100, default="",blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE, related_name='user_id')
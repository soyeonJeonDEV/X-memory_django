
# Create your views here.
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from .forms import UserForm, PhotoForm
from .models import Photo
import logging
import boto3
from botocore.exceptions import ClientError
import os
import time
import mimetypes
# import models
# import requests

@login_required(login_url='login')
def index(request):
  """
  album
  """
  # 유저 조회
  user = get_user_model()

  # mysql에서 s3 url 리스트 가져옴
  photo_list=Photo.objects.filter(author_id=request.user.id).values_list('photo', flat=True)

  #url 리스트 생성 
  photos=[]  
  for a in photo_list:
    a=a.strip('s3://cloud01-2/')
    url = create_presigned_url('cloud01-2', a)
    print(url)
    if url is not None:
    #   response = requests.get(url)
      photos.append(url)
        
  context = {'photos':photos}
  return render(request, 'album.html', context)


def signup(request):

  if request.method == 'POST':
    form = UserForm(request.POST)

    if form.is_valid():
      form.save()
      username = form.cleaned_data.get('username')
      raw_password  = form.cleaned_data.get('password1')
      user = authenticate(username = username, password = raw_password)
      login(request, user)
      return redirect('/')

  else:
    form = UserForm()

  return render(request, 'signup.html', {'form' : form})



# 사진 업로드 함수
@login_required(login_url='login')
def upload(request): 
  """
  upload
  """
  if request.method== "POST":
    print('request method is post')
    print(request.POST)
    form = PhotoForm(request.POST)
    if form.is_valid():
      post = form.save(commit=False)  

      # title이 입력되지 않으면 현재날짜를 title로 넣어줌
      if post.title == None:
        post.title=timezone.localdate()

      # photo가 입력되었는지 확인하고 넣어줌
      if 'photo' in request.FILES:
        post.photo=request.FILES['photo']
        
        # s3업로드
        photo_object_key='public/'+str(request.user.username)+'/'+str(post.photo)
        s3_upload_file(post.photo,'cloud01-2',photo_object_key)
        
        # s3링크저장
        s3url = 's3://cloud01-2/'+photo_object_key
        post.photo=s3url

      # author, create_date 지정
      post.author= request.user
      post.create_date=timezone.now()

      # 세이브
      post.save()
      print('post save made')

      return redirect('index')

    else:
      print('form is not valid')

  else:
    print('request method is get -upload')
    form=PhotoForm()
    
  context = {'form': form }
  return render(request, 'upload.html', context )



#사진 삭제
@login_required(login_url='common:login')
def delete(request,post_id):
  if request.method== "GET":
    print('request method is get. - views.post_delete')
    post = get_object_or_404(models.Photo, pk=post_id)
    form = PhotoForm(request.POST)
    if form.is_valid():
      print('form is valid -delete')
      post.delete()
    else:
      print('post delete - form is not valid')

  return redirect('dailyphoto:profile', username = request.user.username)


def s3_upload_file(file_obj, bucket, object_name=None):
  """Upload a file to an S3 bucket

  :param file_name: File to upload
  :param bucket: Bucket to upload to
  :param object_name: S3 object name. If not specified then file_name is used
  :return: True if file was uploaded, else False
  """

  # If S3 object_name was not specified, use file_name
  basename=str(file_obj)

  if object_name is None:
      object_name = basename
  
  #확장자명 
  extension= str(basename).split('.')[-1]

  # Upload the file
  s3_client = boto3.client('s3')
  try:
      response = s3_client.upload_fileobj(file_obj, bucket, object_name,{'ContentType':extension})
      
  except ClientError as e:
      logging.error(e)
      return False
  return True


# 프리사인드 url 생성 함수 
# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html
def create_presigned_url(bucket_name, object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_url('get_object',Params={'Bucket': bucket_name,'Key': object_name},ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response
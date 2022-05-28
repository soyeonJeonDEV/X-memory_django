
# Create your views here.
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
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


@login_required(login_url='login')
def index(request):
  """
  album
  """
  # 조회
  user = get_user_model()

  # print(request.user.id)
  # print(request.user.username)

        
  context = {}
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


# 글 업로드 함수
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




def s3_upload_file(file_name, bucket, object_name=None):
  """Upload a file to an S3 bucket

  :param file_name: File to upload
  :param bucket: Bucket to upload to
  :param object_name: S3 object name. If not specified then file_name is used
  :return: True if file was uploaded, else False
  """

  # If S3 object_name was not specified, use file_name
  if object_name is None:
      object_name = os.path.basename(file_name)

  # Upload the file
  s3_client = boto3.client('s3')
  try:
      response = s3_client.upload_fileobj(file_name, bucket, object_name)
  except ClientError as e:
      logging.error(e)
      return False
  return True

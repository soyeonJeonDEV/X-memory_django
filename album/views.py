
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
import mimetypes

@login_required(login_url='login')
def index(request):
  """
  album
  """
  # 조회
  user = get_user_model()

  # mysql에서 s3 url 리스트 가져옴

  # photos= Photo.objects.all()
  # print(photos)
  # photos=Photo.objects.all().values('photo')
  # print(photos)
  # photos=Photo.objects.filter(author_id= request.user.id)
  # print(photos)
  # photos=Photo.objects.filter(author_id=request.user.id).values('photo')
  # print(photos)
  # photos= list(map(slice_by_1,list(photos)))
  # print(photos)
  photo_list=Photo.objects.filter(author_id=request.user.id).values_list('photo', flat=True)
  # print(photo_list)


  # s3에서 이미지 가져오기?
  # 직링은 안되나?
  # 안됨
  # 그럼.........

#  검색해본결과 s3에서 다운로드 대신 인라인 로딩을 하려면 저장할때부터 mimetype을 지정해놓고 저장해야한다고 한다 그럼 지금이랑 다른건가??
#mimetype 모듈 사용이 os.path가아니라 imagefieldfile이라 안된다고 한다. 파일 이름을 가져와서 마지막 확장자를 ContentType으로 넣었다 
  s3 = boto3.resource('s3')
  bucket = s3.Bucket('cloud01-2')
# Iterates through all the objects, doing the pagination for you. Each obj
# is an ObjectSummary, so it doesn't contain the body. You'll need to call
# get to get the whole body.
  # for obj in bucket.objects.filter(author_id=request.user.id):
  # for obj in bucket.objects.all():
  #   key = obj.key
  #   print(key)
  #   # a = obj.get(photos[0])
  #   # a=obj.key(photos[0])
  #   # print(a)
  #   # b = a['body']
  #   # print(b)

  #   body = obj.get()['Body'].read()
  #   # print(body)
  #   photos.append(body)
  photos=[]  
  for a in photo_list:
    a=a.strip('s3://cloud01-2/')
    url = create_presigned_url('cloud01-2', a)
    print(url)
    # if url is not None:
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




def s3_upload_file(file_obj, bucket, object_name=None):
  """Upload a file to an S3 bucket

  :param file_name: File to upload
  :param bucket: Bucket to upload to
  :param object_name: S3 object name. If not specified then file_name is used
  :return: True if file was uploaded, else False
  """

  # If S3 object_name was not specified, use file_name
  # basename = os.path.basename(file_obj)
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
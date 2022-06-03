
# Create your views here.
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.shortcuts import redirect, render,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from .forms import UserForm, PhotoForm
from .models import Photo, PhotoTag
import logging
import boto3
from botocore.exceptions import ClientError
from django.views.decorators.csrf import csrf_exempt
import os
import time
import mimetypes
# import models
# import requests
# import jsonresponse

import io
from PIL import Image
import cv2
import numpy as np
from base64 import b64decode
# from .utils import *
# from .Darknet import DarkNet

@login_required(login_url='login')
def index(request):
  """
  album
  """
  # 유저 조회
  user = get_user_model()

  # mysql에서 s3 url 리스트 가져옴
  photo_list=Photo.objects.filter(author_id=request.user.id)
  url_list= photo_list.values_list('photo', flat=True)
  id_list=list(photo_list.values_list('id',flat=True))

  #url 리스트 생성 
  photos=[]
  count=0  
  # id=[]
  for a in url_list:
    if (a[0]=='s') :
      url=a.strip('s3://cloud01-2/')
      # print(url)
      url = create_presigned_url('cloud01-2', url)
      # print(url)
    else:
      url=a
    print(url)
    if url is not None:
    #   response = requests.get(url)
      photos.append({'url':url,'id':id_list[count]})
      count +=1

  print (photos)      
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

      # # title이 입력되지 않으면 현재날짜를 title로 넣어줌
      # if post.title == None:
      #   post.title=timezone.localdate()

      # photo가 입력되었는지 확인하고 넣어줌
      if 'photo' in request.FILES:
        post.photo=request.FILES['photo']
        
        # s3업로드
        photo_object_key='public/'+str(request.user.username)+'/'+str(post.photo)
        s3_upload_file(post.photo,'cloud01-2',photo_object_key)
        
        # s3링크저장
        # s3url = 's3://cloud01-2/'+photo_object_key
        s3url=create_url('cloud01-2',photo_object_key)
        post.photo=s3url

      # author, create_date 지정
      post.author= request.user
      # post.create_date=timezone.now()

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
    post = get_object_or_404(Photo, pk=post_id)
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


# url 생성 함수
def create_url(bucket_name,object_key):
  return f'https://{bucket_name}.s3.us-east-2.amazonaws.com/{object_key}'


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




# @csrf_exempt
# def object_detection_api(api_request):
#     json_object = {'success': False}

#     if api_request.method == "POST":

#         if api_request.POST.get("image64", None) is not None:
#             base64_data = api_request.POST.get("image64", None).split(',', 1)[1]
#             data = b64decode(base64_data)
#             data = np.array(Image.open(io.BytesIO(data)))
#             result, detection_time = detection(data)

#         elif api_request.FILES.get("image", None) is not None:
#             image_api_request = api_request.FILES["image"]
#             image_bytes = image_api_request.read()
#             image = Image.open(io.BytesIO(image_bytes))
#             result, detection_time = detection(image, web=False)

#     if result:
#         json_object['success'] = True
#     json_object['time'] = str(round(detection_time))+" seconds"
#     json_object['objects'] = result
#     print(json_object)
#     return JsonResponse(json_object)


# def detect_request(api_request):
#     # return render(api_request, 'index.html')
#     return render(api_request, 'test.html')


# def detection(original_image, web=True):
#     cfg_file = './yolov3-tiny-custom.cfg'
#     weight_file = './yolov3-tiny-custom_final.weights'
#     names = './coco.names'

#     m = DarkNet(cfg_file)
#     m.load_weights(weight_file)
#     class_names = load_coco_names(names)

#     resized_image = cv2.resize(np.float32(original_image), (m.width, m.height))
#     nms_thresh = 0.018
#     iou_thresh = 0.2

#     boxes, detection_time = detect_objects(m, resized_image, iou_thresh, nms_thresh)
#     objects = label_objects(boxes, class_names)

#     if web:
#         plot_object_boxes(original_image, boxes, class_names)

#     return objects, detection_time


def test():
  pass


def detail(request,photo_id):
  photo=Photo.objects.filter(id=photo_id)
  photo=photo.values('photo')
  # print(photo)
  photo=list(photo)[0]['photo']
  # print(photo)

  if (photo[0]=='s') :
    url=photo.strip('s3://cloud01-2/')
    # print(url)
    url = create_presigned_url('cloud01-2', url)
    print(url)
  else:
    url=photo  

  tags=PhotoTag.objects.filter(photo_id=photo_id)
  print (tags)
  tags=['더미태그1','더미태그2','더미태그3']
  return render(request, 'detail.html', {'tags' : tags,'photo_id':photo_id,'photo':url})

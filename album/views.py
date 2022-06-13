
# Create your views here.
from calendar import week
import datetime
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from requests import request
from .forms import UserForm, PhotoForm,TagForm
from .models import Photo, PhotoTag, Analysis, AnalysisResult
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
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

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.http import JsonResponse
from django.views.generic import View

import pandas as pd
import pymysql
import collections
import googlemaps
from PIL import Image
import matplotlib.pyplot as plt
from folium import plugins
import folium
from matplotlib import font_manager, rc
import seaborn as sns


#위치 가져오기 위해 api접근
gmaps= googlemaps.Client(key='AIzaSyDlTe2iwy53wvvt8WNwJ15fgzLGNmAQpf8')
  
# presigned 아닌 사진 리스트
@login_required(login_url='login')
def index(request):
    """
    album
    """
    # 조회
    user = get_user_model()
    photo_list = Photo.objects.filter(author_id=request.user.id).values_list('photo', flat=True)
    id_list = list(photo_list.values_list('id', flat=True))
    photos = []
    count = 0
    for a in photo_list:
        if a is not None:
            #   response = requests.get(url)
            photos.append({'url': a, 'id': id_list[count]})
            count += 1
    context = {'photos': photos}
    return render(request, 'album.html', context)


def signup(request):
    if request.method == 'POST':
        form = UserForm(request.POST)

        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('/')

    else:
        form = UserForm()

    return render(request, 'signup.html', {'form': form})


# 사진 업로드 함수
@login_required(login_url='login')
def upload(request):
    """
    upload
    """
    if request.method == "POST":
        print('request method is post')
        print(request.POST)
        form = PhotoForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)

            # photo가 입력되었는지 확인하고 넣어줌
            if 'photo' in request.FILES:
                photo = request.FILES['photo']
                photo_read = photo.read()
                photo.seek(0)

                # s3업로드
                photo_object_key = 'public/' + str(request.user.username) + '/' + str(photo)
                s3_upload_file(photo, 'cloud01-2', photo_object_key)

                # s3링크저장
                # s3url = 's3://cloud01-2/'+photo_object_key
                s3url = create_url('cloud01-2', photo_object_key)
                post.photo = s3url

                # author, create_date 지정
                post.author = request.user
                # post.create_date=timezone.now()

                # 세이브
                post.save()
                print('post save made')

                # 태그 자동 삽입
                # try:
                taglist = yolo(photo_read)
                # print(taglist)
                photo_object = Photo.objects.filter(photo=s3url)
                photo_object = photo_object[len(photo_object) - 1]
                print(photo_object)
                for a_tag in taglist:
                    tagForm = TagForm({'photo': photo_object, 'tags': a_tag, 'create_date': timezone.now()})
                    # print(tagForm)
                    if tagForm.is_valid():
                        tagForm.save()
                    else:
                        print('tagform is not valid')
                        print(tagForm.errors)

                # except:
                # print('yolo 태그 검출 실패')

            return redirect('index')

        else:
            print('form is not valid')

    else:
        print('request method is get -upload')
        form = PhotoForm()

    context = {'form': form}
    return render(request, 'upload.html', context)


# 사진 삭제
@login_required(login_url='common:login')
def delete(request, post_id):
    if request.method == "GET":
        print('request method is get. - views.post_delete')
        post = get_object_or_404(Photo, pk=post_id)
        form = PhotoForm(request.POST)
        if form.is_valid():
            print('form is valid -delete')
            post.delete()
        else:
            print('post delete - form is not valid')

    return redirect('dailyphoto:profile', username=request.user.username)


def s3_upload_file(file_obj, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    basename = str(file_obj)

    if object_name is None:
        object_name = basename

    # 확장자명
    extension = str(basename).split('.')[-1]

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_fileobj(file_obj, bucket, object_name, {'ContentType': extension})

    except ClientError as e:
        logging.error(e)
        return False
    return True


# url 생성 함수
def create_url(bucket_name, object_key):
    return f'https://{bucket_name}.s3.us-east-2.amazonaws.com/{object_key}'


# 프리사인드 url 생성 함수
# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html
def create_presigned_url(bucket_name, object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object

    :param bucket_name: string
    :param object_name: string
    :param expiration: Time in seconds for the pres valid
    :return: Presigned URL as string. If error, returns None.
    """

    # Generate a presigned URL for the S3 object
    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': object_name},
                                                    ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response


def s3_get(bucket, key):
    s3_client = boto3.client('s3')
    try:
        print(key)
        response = s3_client.get_object(Bucket=bucket, Key=key)
        print(f'response = {response}')
        content = response['Body'].read()
        # print(f'content = {content}')
        return content

    except ClientError as e:
        logging.error(e)
        return False
    return True


def detail(request, photo_id):
    photo = Photo.objects.filter(id=photo_id)
    photo = photo.values('photo')
    # print(photo)
    photo = list(photo)[0]['photo']
    print(photo)

    if (photo[0] == 's'):
        url = photo.strip('s3://cloud01-2/')
        # print(url)
        url = create_presigned_url('cloud01-2', url)
        print(url)
    else:
        url = photo

    tags = PhotoTag.objects.filter(photo_id=photo_id).values_list('tags', flat=True)

    # 태그가 존재하는가
    if tags:
        tags = list(tags)
        print(f'tags{tags}')

    # 태그가 없을 경우 자동검출
    else:
        # tags=리스트 스트링
        # tags= yolo(photo.read())
        key = 'pu' + url.strip('https://cloud01-2.s3.us-east-2.amazonaws.com')  # 앞에 두글자 짤리는 이유가 뭔지 모르겠다
        pic = s3_get('cloud01-2', key)
        # print(pic)
        tags = yolo(pic)
        print(tags)

        # 태그 저장
        for a_tag in tags:
            print(a_tag)
            tagForm = TagForm(
                {'tags': a_tag, 'photo': Photo.objects.get(id=int(photo_id)), 'create_date': timezone.now()})
            print(tagForm)
            if tagForm.is_valid():
                tagForm.save()

            else:
                print('tagform is not valid')
                print(tagForm.errors)

    # analysis(request)

    return render(request, 'detail.html', {'tags': tags, 'photo_id': photo_id, 'photo': url})


@csrf_exempt
def search_by_tag(request):
    print('search_by_tag 함수')
    tag=request.GET['tag']
    print(tag)
    # print(request.body)
    # print(request.GET)

    photo_list = []
    photo_result= PhotoTag.objects.filter(tags=tag).values_list('photo_id',flat=True)
    print(photo_result)
    for a_photo_id in photo_result:
        print(a_photo_id)
        found_photo=Photo.objects.get(id=a_photo_id)
        if found_photo.author == request.user:
            print(found_photo.photo_id)
            photo_list.append({'url':str(found_photo.photo),'id':str(found_photo.id)})
    
    print(photo_list)

    return render (request,'search.html',{'tag':tag,'photo_list' : photo_list})



def s3_get(bucket,key):
  
  s3_client = boto3.client('s3')
  try:
    print(key)
    response = s3_client.get_object(Bucket=bucket, Key=key)
    print(f'response = {response}')
    content=response['Body'].read()
    # print(f'content = {content}')
    return content
      
  except ClientError as e:
      logging.error(e)
      return False
  return True


def detail(request,photo_id):
  photo=Photo.objects.filter(id=photo_id)
  photo=photo.values('photo')
  # print(photo)
  photo=list(photo)[0]['photo']
  print(photo)

  if (photo[0]=='s') :
    url=photo.strip('s3://cloud01-2/')
    # print(url)
    url = create_presigned_url('cloud01-2', url)
    print(url)
  else:
    url=photo  

  tags=PhotoTag.objects.filter(photo_id=photo_id).values_list('tags',flat=True)

  # 태그가 존재하는가 
  if tags:
    tags=list(tags)
    print(f'tags{tags}')
  
  # 태그가 없을 경우 자동검출 
  else:
    # tags=리스트 스트링
    # tags= yolo(photo.read())
    key ='pu'+ url.strip('https://cloud01-2.s3.us-east-2.amazonaws.com') #앞에 두글자 짤리는 이유가 뭔지 모르겠다 
    pic= s3_get('cloud01-2',key)
    # print(pic)
    tags= yolo(pic)
    print(tags)

    # 태그 저장 
    for a_tag in tags:
      print(a_tag)
      tagForm= TagForm({'tags':a_tag,'photo':Photo.objects.get(id=int(photo_id)),'create_date':timezone.now()})
      print(tagForm)
      if tagForm.is_valid():
        tagForm.save()

      else:
        print('tagform is not valid')
        print(tagForm.errors)


  # analysis(request)

  return render(request, 'detail.html', {'tags' : tags,'photo_id':photo_id,'photo':url})



def yolo(img_buffer):
    # Load Yolo
    net = cv2.dnn.readNet("album\yolov3-tiny-custom_final.weights", "album\yolov3-tiny-custom.cfg")
    classes = []
    with open("album\coco.names", "r") as f:
        classes = [line.strip() for line in f.readlines()]
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
    # output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
    colors = np.random.uniform(0, 255, size=(len(classes), 3))

    # Loading image
    img = cv2.imdecode(np.frombuffer(img_buffer, np.uint8), -1)
    img = cv2.resize(img, None, fx=0.4, fy=0.4)
    height, width, channels = img.shape

    # Detecting objects
    blob = cv2.dnn.blobFromImage(img, 0.00392, (416, 416), (0, 0, 0), True, crop=False)

    net.setInput(blob)
    outs = net.forward(output_layers)

    class_ids = []
    confidences = []
    boxes = []
    tag = []
    labels = []
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.3:
                # Object detected
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)

                # Rectangle coordinates
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)

                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        print(indexes)

        font = cv2.FONT_HERSHEY_PLAIN

        for i in range(len(boxes)):
            if i in indexes:
                x, y, w, h = boxes[i]
                label = str(classes[class_ids[i]])
                labels.append(label)
                # color = colors[class_ids[i]]
                # cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
                # cv2.putText(img, label, (x, y + 30), font, 3, color, 3)


                for i in range(len(boxes)):
                  tag.append(classes[class_ids[i]])
                  
                tag = set(tag)
                
        # cv2.imshow("Image", img)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        print('태그: ' + str(tag))

    return tag


@login_required(login_url='login')
def add_tag(request):
  print('add_tag 실행')
  # print(request)
  print(request.POST)
  # print(request.body)
  if request.method=="POST":
    form = TagForm(request.POST)
    if form.is_valid():
      print('form is valid')
      tagform=form.save(commit=False)
      # print(request.POST['photo'])
      tagform.photo=Photo.objects.get(id=int(request.POST['photo']))
      print(tagform.photo)
      # print(request.POST['tags'])
      tagform.tags=request.POST['tags']
      # print(tags.tags)
      # print(tags)
      tagform.create_date=timezone.now()
      print(tagform.create_date)
      tagform.save()
      
      return JsonResponse({'code': '200', 'msg': '태그 전송 성공'})
    else:
        print('add_tag if문 빠져나옴 - request method is not post')

    return JsonResponse({'code': '500', 'msg': '태그 전송 실패'})


@login_required(login_url='login')
def detect_tag(request):
    print('사물 검출')
    print(request)
    print(request.POST)
    print(request.body)
    if request.method == "POST":
        form = TagForm(request.POST)
        if form.is_valid():
            # Load Yolo
            net = cv2.dnn.readNet("album\yolov3-tiny-custom_final.weights", "album\yolov3-tiny-custom.cfg")
            classes = []
            with open("album\coco.names", "r") as f:
                classes = [line.strip() for line in f.readlines()]
            layer_names = net.getLayerNames()
            output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
            # output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
            colors = np.random.uniform(0, 255, size=(len(classes), 3))

            # Loading image
            img = cv2.imread('album\94.jpg')
            img = cv2.resize(img, None, fx=0.4, fy=0.4)
            height, width, channels = img.shape

            # Detecting objects
            blob = cv2.dnn.blobFromImage(img, 0.00392, (416, 416), (0, 0, 0), True, crop=False)

            net.setInput(blob)
            outs = net.forward(output_layers)

            class_ids = []
            confidences = []
            boxes = []
            for out in outs:
                for detection in out:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    if confidence > 0.5:
                        # Object detected
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)

                        # Rectangle coordinates
                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)

                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)

                indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
                print(indexes)

                font = cv2.FONT_HERSHEY_PLAIN
                for i in range(len(boxes)):
                    if i in indexes:
                        x, y, w, h = boxes[i]
                        label = str(classes[class_ids[i]])
                        # color = colors[class_ids[i]]
                        # cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
                        # cv2.putText(img, label, (x + 15, y + 110), font, 3, color, 2)

                    # cv2.imshow("Image", img)
                    # cv2.waitKey(0)
                    # cv2.destroyAllWindows()

                print('#' + label)  # 해시태그

        else:
            print(form.errors.as_data())
            print('form is not valid')
    else:
        print('사물 검출 if문 빠져나옴 - request method is not post')

    return HttpResponse()


##태그테이블에서 위경도를 받아와서 위치를 찾는 함수
def search_place(tag_table):
    photo = tag_table.drop_duplicates(['photo_id'])
    place = photo[['longitude', 'latitude']]
    if place.empty == False:
        place = place.fillna(0)
        __list__=[]
        for row in place.itertuples(index=False, name=None):
            if row == (0,0):
                __list__.append(0)
            else:
                try:
                    geo_location=gmaps.reverse_geocode(row, language='ko')
                    __list__.append(pd.DataFrame(geo_location)['formatted_address'][0])      
                except:
                    __list__.append(0)
        photo = photo.copy()
    photo['place']= __list__
    tag_table=pd.merge(tag_table,photo[['photo_id','place']], how='left', left_on='photo_id', right_on='photo_id')
    return tag_table
    


# @login_required(login_url='login')
@csrf_exempt
def analysis(request):
    try:
        date = request.GET['date']

    except: #기본 페이지(현재 날짜)

        user = get_user_model()
        user = request.user.id
        photo_id_list = list(Photo.objects.filter(author_id=user).values_list('id', flat=True))
        if photo_id_list == []:
            rank1_tagname = 0
            content = {
                'rank1_tagname' : 'NO PHOTO'
                }
            return render(request, 'analysis.html', content)
        photo_id = ','.join(map(str, photo_id_list))
        # MySQL Connection 연결하고 테이블에서 데이터 가져옴
        tag_table = get_table(user, photo_id, 'phototag')

        if tag_table.empty == False:
            year = datetime.datetime.now().year
            month = datetime.datetime.now().month

            tag_table['create_date'] = pd.to_datetime(tag_table['create_date'])
            tag_table['year'] = tag_table['create_date'].dt.year
            tag_table['month'] = tag_table['create_date'].dt.month
            tag_table = tag_table[(tag_table['year'] == year) & (tag_table['month'] == month)]  # 연도,월 일치하는 데이터만 가져옴
            # tag_table은 사용자가 요청한 연/월에 맞는 사용자의 phototag
            # 태그 Top3에 대한 태그명, 태그 개수 구하기 ###########
            ## new tag list
            if tag_table.empty == False: #태그테이블에 값 있어야 시작
                tags_lst = tag_table['tags'] 
                ## Tag top 3 # 
                rank3 = collections.Counter(tags_lst).most_common(3) #태그 개수가 3개 안되면 오류날듯,,?
                ## tag name (rank1~3)
                rank3_name = [list(row)[0] for row in rank3] 
                rank1_tagname = rank3_name[0]
                rank2_tagname = rank3_name[1]
                rank3_tagname = rank3_name[2]

                ## tag frequency (rank1~3)
                rank3_freq = [list(row)[1] for row in rank3]
                rank1_tagfreq = rank3_freq[0]
                rank2_tagfreq = rank3_freq[1]
                rank3_tagfreq = rank3_freq[2]

                # 태그 top3에 대해 각각 2개의 연관태그 생성 ###########
                ## 태그 rank1를 가진 사진 id
                related_photo1 = tag_table[tag_table['tags'] == rank1_tagname]['photo_id']
                ## 태그 rank1에 대한 연관 태그
                related_tags1 = tag_table[(tag_table['photo_id'].isin(related_photo1))&(tag_table['tags'].ne(rank1_tagname))&
                                            (tag_table['tags'].ne(rank2_tagname))&(tag_table['tags'].ne(rank3_tagname))]['tags'] #수정
                related_tags1_top2 = collections.Counter(related_tags1).most_common(2)  # 가장 많은 top2만
                ## 태그 rank1에 대한 연관 태그 2개 각각 변수로 저장
                rank1_related_tagname = [list(row)[0] for row in related_tags1_top2]
                related_tagname1_1 = rank1_related_tagname[0]
                related_tagname1_2 = rank1_related_tagname[1]

                ## 태그 rank2를 가진 사진 id
                related_photo2 = tag_table[tag_table['tags'] == rank2_tagname]['photo_id']
                ## 태그 rank2에 대한 연관 태그
                related_tags2 = tag_table[(tag_table['photo_id'].isin(related_photo2))&(tag_table['tags'].ne(rank1_tagname))&
                                            (tag_table['tags'].ne(rank2_tagname))&(tag_table['tags'].ne(rank3_tagname))]['tags'] #수정
                related_tags2_top2 = collections.Counter(related_tags2).most_common(2)  # 가장 많은 top2만
                ## 태그 rank2에 대한 연관 태그 2개 각각 변수로 저장
                rank2_related_tagname = [list(row)[0] for row in related_tags2_top2]
                related_tagname2_1 = rank2_related_tagname[0]
                related_tagname2_2 = rank2_related_tagname[1]

                ## 태그 rank3를 가진 사진 id
                related_photo3 = tag_table[tag_table['tags'] == rank3_tagname]['photo_id']
                ## 태그 rank3에 대한 연관 태그
                related_tags3 = tag_table[(tag_table['photo_id'].isin(related_photo3))&(tag_table['tags'].ne(rank1_tagname))&
                                            (tag_table['tags'].ne(rank2_tagname))&(tag_table['tags'].ne(rank3_tagname))]['tags'] # 수정
                related_tags3_top2 = collections.Counter(related_tags3).most_common(2)  # 가장 많은 top2만
                ## 태그 rank3에 대한 연관 태그 2개 각각 변수로 저장
                rank3_related_tagname = [list(row)[0] for row in related_tags3_top2]
                if len(rank3_related_tagname) == 2: 
                    related_tagname3_1 = rank3_related_tagname[0]
                    related_tagname3_2 = rank3_related_tagname[1]
                else:
                    related_tagname3_1 = 0 
                    related_tagname3_2 = 0

                # rank1 태그의 사진 가져오기 # 수정
                photo1 = Photo.objects.filter(id__in=related_photo1).first()
                photourl = photo1.photo



                content = {
                    'rank1_tagname': rank1_tagname,  # 태그명
                    'rank2_tagname': rank2_tagname,
                    'rank3_tagname': rank3_tagname,
                    'rank1_tagfreq': rank1_tagfreq,  # 태그 빈도
                    'rank2_tagfreq': rank2_tagfreq,
                    'rank3_tagfreq': rank3_tagfreq,
                    'related_tagname1_1': related_tagname1_1,  # 연관 태그명
                    'related_tagname1_2': related_tagname1_2,
                    'related_tagname2_1': related_tagname2_1,
                    'related_tagname2_2': related_tagname2_2,
                    'related_tagname3_1': related_tagname3_1,
                    'related_tagname3_2': related_tagname3_2,
                    'photourl': photourl
                }
            

            else:
                content = {
                    'rank1_tagname': 'NO PHOTO',  # 태그명
                }

        else:
            # pass #리턴할 값이 없으면 오류가 나므로 리턴값을 넣어주세요(현재는 페이지만 띄워줘서 pass했습니다)
            content = {
                'rank1_tagname': 'NO PHOTO',  # 태그명
            }
            
        
        
        #==========================================================================
        #분석 페이지가 아니라 디테일 페이지 들어갔을 때 위치정보 저장받을 수 있도록 수정하기

        # 페이지 접속하면 위치 정보 찾아줌
        analyzed_photo_list = list(Analysis.objects.filter(user_id=user).values_list('photo_id', flat=True))
        N_anaylazed_photos = list(set(photo_id_list) - set(analyzed_photo_list))
        N_anaylazed_photo = ','.join(map(str, N_anaylazed_photos))
        if N_anaylazed_photo:
            tag_table = get_table(user, N_anaylazed_photo, 'phototag')

            # 이미 위치정보가 저장된 사진에 대해서는 위치 찾는 함수 작동X ->DB에 위치정보가 계속 저장되는 것을 막음

            if tag_table.empty == False:
                tag_table['user_id'] = user
                tag_table = search_place(tag_table)

                # 분석한 내용 db로 보내기
                lst = []
                tag_table = tag_table.drop_duplicates(['photo_id'], keep='last')
                for row in tag_table[['photo_id', 'place', 'user_id']].itertuples(index=False, name=None):
                    lst.append(row)
                tuple(lst)

                conn = pymysql.connect(host='18.223.252.140', user='python', password='python', db='mysql_db',
                                    charset='utf8')
                curs = conn.cursor(pymysql.cursors.DictCursor)
                sql = """insert into album_analysis(photo_id,location,user_id) 
                values (%s, %s, %s)"""
                curs.executemany(sql, lst)
                conn.commit()
                conn.close()
        
        # ==============================================================================
        return render(request, 'analysis.html', content) # 현재 월에 해당하는 분석값을 리턴 
#=========================================================================================
 #사용자 요청 받은 날짜 페이지
    user = get_user_model()
    user = request.user.id
    photo_id_list = list(Photo.objects.filter(author_id=user).values_list('id', flat=True))
    if photo_id_list == []:
        return render(request, 'analysis.html')
    photo_id = ','.join(map(str, photo_id_list))
    # MySQL Connection 연결하고 테이블에서 데이터 가져옴
    tag_table = get_table(user, photo_id, 'phototag')

    year, month = date.split('-')
    year = int(year); month = int(month)

    if tag_table.empty == False:
        # 태그테이블에 데이터 존재하면 사용자 요청 받은 날짜인지 비교
        tag_table['create_date'] = pd.to_datetime(tag_table['create_date'])
        tag_table['year'] = tag_table['create_date'].dt.year
        tag_table['month'] = tag_table['create_date'].dt.month

        tag_table = tag_table[(tag_table['year'] == year) & (tag_table['month'] == month)]  # 연도,월 일치하는 데이터만 가져옴

        # tag_table은 사용자가 요청한 연/월에 맞는 사용자의 phototag
        # 태그 Top3에 대한 태그명, 태그 개수 구하기 ###########
        ## new tag list
        if tag_table.empty == False:
            tags_lst = tag_table['tags']

            ## Tag top 3
            rank3 = collections.Counter(tags_lst).most_common(3)
            ## tag name (rank1~3)
            rank3_name = [list(row)[0] for row in rank3]
            rank1_tagname = rank3_name[0]
            rank2_tagname = rank3_name[1]
            rank3_tagname = rank3_name[2]

            ## tag frequency (rank1~3)
            rank3_freq = [list(row)[1] for row in rank3]
            rank1_tagfreq = rank3_freq[0]
            rank2_tagfreq = rank3_freq[1]
            rank3_tagfreq = rank3_freq[2]

            # 태그 top3에 대해 각각 2개의 연관태그 생성 ###########
            ## 태그 rank1를 가진 사진 id
            related_photo1 = tag_table[tag_table['tags'] == rank1_tagname]['photo_id']
            ## 태그 rank1에 대한 연관 태그
            related_tags1 = tag_table[(tag_table['photo_id'].isin(related_photo1))&(tag_table['tags'].ne(rank1_tagname))&
                                        (tag_table['tags'].ne(rank2_tagname))&(tag_table['tags'].ne(rank3_tagname))]['tags'] #수정
            related_tags1_top2 = collections.Counter(related_tags1).most_common(2)  # 가장 많은 top2만
            ## 태그 rank1에 대한 연관 태그 2개 각각 변수로 저장
            rank1_related_tagname = [list(row)[0] for row in related_tags1_top2]
            related_tagname1_1 = rank1_related_tagname[0]
            related_tagname1_2 = rank1_related_tagname[1]

            ## 태그 rank2를 가진 사진 id
            related_photo2 = tag_table[tag_table['tags'] == rank2_tagname]['photo_id']
            ## 태그 rank2에 대한 연관 태그
            related_tags2 = tag_table[(tag_table['photo_id'].isin(related_photo2))&(tag_table['tags'].ne(rank1_tagname))&
                                        (tag_table['tags'].ne(rank2_tagname))&(tag_table['tags'].ne(rank3_tagname))]['tags'] #수정
            related_tags2_top2 = collections.Counter(related_tags2).most_common(2)  # 가장 많은 top2만
            ## 태그 rank2에 대한 연관 태그 2개 각각 변수로 저장
            rank2_related_tagname = [list(row)[0] for row in related_tags2_top2]
            related_tagname2_1 = rank2_related_tagname[0]
            related_tagname2_2 = rank2_related_tagname[1]

            ## 태그 rank3를 가진 사진 id
            related_photo3 = tag_table[tag_table['tags'] == rank3_tagname]['photo_id']
            ## 태그 rank3에 대한 연관 태그
            related_tags3 = tag_table[(tag_table['photo_id'].isin(related_photo3))&(tag_table['tags'].ne(rank1_tagname))&
                                        (tag_table['tags'].ne(rank2_tagname))&(tag_table['tags'].ne(rank3_tagname))]['tags'] # 수정
            related_tags3_top2 = collections.Counter(related_tags3).most_common(2)  # 가장 많은 top2만
            ## 태그 rank3에 대한 연관 태그 2개 각각 변수로 저장
            rank3_related_tagname = [list(row)[0] for row in related_tags3_top2]
            related_tagname3_1 = rank3_related_tagname[0]
            related_tagname3_2 = rank3_related_tagname[1]


            # rank1 태그의 사진 가져오기 # 수정
            photo1 = Photo.objects.filter(id__in=related_photo1).first()
            photourl = photo1.photo
            content = {
                'rank1_tagname': rank1_tagname,  # 태그명
                'rank2_tagname': rank2_tagname,
                'rank3_tagname': rank3_tagname,
                'rank1_tagfreq': rank1_tagfreq,  # 태그 빈도
                'rank2_tagfreq': rank2_tagfreq,
                'rank3_tagfreq': rank3_tagfreq,
                'related_tagname1_1': related_tagname1_1,  # 연관 태그명
                'related_tagname1_2': related_tagname1_2,
                'related_tagname2_1': related_tagname2_1,
                'related_tagname2_2': related_tagname2_2,
                'related_tagname3_1': related_tagname3_1,
                'related_tagname3_2': related_tagname3_2,
                'photourl': photourl
            }
        else:
            content = {
                'rank1_tagname': '사진이 없습니다',  # 태그명
            }

    else:

        content = {
            'rank1_tagname': '사진이 없습니다',  # 태그명
        }


    return render(request, 'analysis.html', content )  # ,{'map' : maps}


# photo_id 참조하여 DB에서 정보 가져오는 함수
"""
  user = get_user_model()
  user = user.id
  photo_id_list=list(Photo.objects.filter(author_id=request.user).values_list('id', flat=True))
  photo_id=','.join(map(str, photo_id_list))
"""


# 함수 쓸 때 위에 있어야 하는 문장 사용:get_table(user,photo_id, 가져오고자 하는 테이블명)
# DBtable: 'analysis', 'photo', 'phototag
def get_table(user, photo_id, DBtable):
    # MySQL Connection 연결하고 테이블에서 데이터 가져옴
    conn = pymysql.connect(host='18.223.252.140', user='python', password='python', db='mysql_db', charset='utf8')
    curs = conn.cursor(pymysql.cursors.DictCursor)
    sql = 'select * from album_' + DBtable + ' where photo_id in (' + photo_id + ')'

    curs.execute(sql)
    rows = curs.fetchall()
    table = pd.DataFrame(rows)
    return table


# Create your views here.
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from .forms import PhotoForm, DetailForm, ProfileForm
from .models import Photo, ProfileImage

from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.http import JsonResponse

from analysis.views import *


#app_login api
class AppLoginView(APIView):
    def post(self, request):

        print(request.POST)
        id = request.POST.get('userid', '')
        pw = request.POST.get('userpw', '')

        user = authenticate(username=id, password=pw)
        token = Token.objects.get(user=user)

        if user:
            print("로그인 성공!")
            return JsonResponse({'token':token.key, 'code': '200', 'msg': '로그인 성공입니다.'}, status=200)
        else:
            print("실패")
            return JsonResponse({'token':'x','code': '404', 'msg': '로그인 실패입니다.'}, status=404)
            
#app_photo_uri_path save
class UploadView(APIView):
  def post(self,request,format=None):
    form = PhotoForm(request.POST)
    profile = ProfileForm(request.POST)
    photo = request.POST.get('photo','')
    profileImage = photo[:8]
    print(request.POST)

    if form.is_valid():
      if profileImage == "profile/":
        post = profile.save(commit=False)  
          # s3경로 
        s3url = 'https://cloud01-2.s3.us-east-2.amazonaws.com/public/' +str(request.user.username)+'/' + photo
        post.profileImage=s3url
        thumbnail_key = 'public/'+str(request.user.username)+'/'+str(post.profileImage)
        # 썸네일 링크 저장
        thumbnail_url = create_url("cloud01-2-resized", thumbnail_key)
        post.thumbnail = thumbnail_url
        post.user = request.user
        count = ProfileImage.objects.filter(user_id = request.user.id).values_list("user_id", flat=True).count()
        # 세이브
        if count == 0:
          post.save()
          print('post save made')
          return JsonResponse({'id': post.id, 'code': '200', 'msg': '성공입니다.'}, status=200)
        else:
          post.id = ProfileImage.objects.get(user_id = request.user.id).id
          post.save()
          return JsonResponse({ 'code': '200', 'msg': '성공입니다.'}, status=200)
          
      else:
        post = form.save(commit=False)  

          # s3경로 
        s3url = 'https://cloud01-2.s3.us-east-2.amazonaws.com/public/' +str(request.user.username)+'/' + photo
        post.photo=s3url
        thumbnail_key = 'public/'+str(request.user.username)+'/'+str(post.photo)
        # 썸네일 링크 저장
        thumbnail_url = create_url("cloud01-2-resized", thumbnail_key)
        post.thumbnail = thumbnail_url
        post.author = request.user
        

        # 세이브
        post.save()
        print('post save made')

        return JsonResponse({'id': post.id, 'code': '200', 'msg': '성공입니다.'}, status=200)
    else:
      return JsonResponse({'code': '404', 'msg': '실패입니다.'}, status=404)

    

# 앨범 화면 api
class IndexView(APIView):
  def get(self,request,format=None):
    photo_list=Photo.objects.filter(author_id=request.user.id).values_list('photo', flat=True)
    id_list=list(photo_list.values_list('id',flat=True))
    photos=[]
    count = 0
    for a in photo_list:
      if a is not None:
        url = "https://d1e6tpyhrf8oqe.cloudfront.net" + a[44:]
      #   response = requests.get(url)
        photos.append({'url':url,'id':id_list[count]})
        count +=1
    context = {'photos':photos}
    return render(request, 'album2.html', context)
    #   # 조회
    # photo_list=Photo.objects.filter(author_id=request.user.id).values_list('photo', flat=True)
    # id_list=list(photo_list.values_list('id',flat=True))
    # photos=[]
    # count = 0
    # for a in photo_list:
    #   if a is not None:
    #   #   response = requests.get(url)
    #     photos.append({'url':a,'id':id_list[count]})
    #     count +=1
    # context = {'photos':photos}
    # return render(request, 'album.html', context)


# 사진 개수 api
class ProfileView(APIView):
  def post(self,request,format=None):
        # 사진 개수
        count = Photo.objects.filter(author_id=request.user.id).values_list('photo', flat=True).count()
        filename = str(ProfileImage.objects.get(user_id=request.user.id).profileImage)

        print(filename)

        if request.user:
          return JsonResponse({'count':count,'filename':filename, 'code': '200', 'msg': '성공입니다.'}, status=200)
        else:
          return JsonResponse({'code': '404', 'msg': '실패입니다.'}, status=404)

from datetime import datetime
# 위도 경도 db 저장 api
class UploadDetailView(APIView):
  def post(self, request, format=None):
    time = None
    if request.POST.get('time',''):
      time = request.POST.get('time','')
      timeFormat = '%Y:%m:%d %H:%M:%S'
      timedata = datetime.strptime(time,timeFormat)
    if request.method=="POST":
      form = DetailForm(request.POST)
      if form.is_valid():
        tags=form.save(commit=False)
        tags.photo=Photo.objects.get(id=int(request.POST['photo']))
        tags.latitude=request.POST['latitude']
        tags.longitude=request.POST['longitude']
        if time:
          tags.create_date = timedata
          print(tags.create_date)
        else:
          tags.create_date=timezone.now()
        tags.save()

      return JsonResponse({'code': '200', 'msg': '성공입니다.'}, status=200)
    else:
      return JsonResponse({'code': '404', 'msg': '실패입니다.'}, status=404)

class AnalysisView(APIView):
  def get(self,request, format=None):
    try:
        date = request.GET['date']

    except: #기본 페이지(현재 날짜)

        user = get_user_model()
        user = request.user.id
        photo_id_list = list(Photo.objects.filter(author_id=user).values_list('id', flat=True))
        if photo_id_list == []:
            rank1_tagname = 0
            content = {
                'rank1_tagname' : 'NO PHOTO'
                }
            return render(request, 'analysis.html', content)
        photo_id = ','.join(map(str, photo_id_list))
        # MySQL Connection 연결하고 테이블에서 데이터 가져옴
        tag_table = get_table(user, photo_id, 'phototag')

        if tag_table.empty == False:
            year = datetime.datetime.now().year
            month = datetime.datetime.now().month

            tag_table['create_date'] = pd.to_datetime(tag_table['create_date'])
            tag_table['year'] = tag_table['create_date'].dt.year
            tag_table['month'] = tag_table['create_date'].dt.month
            tag_table = tag_table[(tag_table['year'] == year) & (tag_table['month'] == month)]  # 연도,월 일치하는 데이터만 가져옴
            # tag_table은 사용자가 요청한 연/월에 맞는 사용자의 phototag
            # 태그 Top3에 대한 태그명, 태그 개수 구하기 ###########
            ## new tag list
            if tag_table.empty == False:
                tags_lst = tag_table['tags']

                ## Tag top 3
                rank3 = collections.Counter(tags_lst).most_common(3)
                ## tag name (rank1~3)
                rank3_name = [list(row)[0] for row in rank3]
                rank1_tagname = rank3_name[0]
                rank2_tagname = rank3_name[1]
                rank3_tagname = rank3_name[2]

                ## tag frequency (rank1~3)
                rank3_freq = [list(row)[1] for row in rank3]
                rank1_tagfreq = rank3_freq[0]
                rank2_tagfreq = rank3_freq[1]
                rank3_tagfreq = rank3_freq[2]

                # 태그 top3에 대해 각각 2개의 연관태그 생성 ###########
                ## 태그 rank1를 가진 사진 id
                related_photo1 = tag_table[tag_table['tags'] == rank1_tagname]['photo_id']
                ## 태그 rank1에 대한 연관 태그
                related_tags1 = tag_table[(tag_table['photo_id'].isin(related_photo1))&(tag_table['tags'].ne(rank1_tagname))&
                                            (tag_table['tags'].ne(rank2_tagname))&(tag_table['tags'].ne(rank3_tagname))]['tags'] #수정
                related_tags1_top2 = collections.Counter(related_tags1).most_common(2)  # 가장 많은 top2만
                ## 태그 rank1에 대한 연관 태그 2개 각각 변수로 저장
                rank1_related_tagname = [list(row)[0] for row in related_tags1_top2]
                related_tagname1_1 = rank1_related_tagname[0]
                related_tagname1_2 = rank1_related_tagname[1]

                ## 태그 rank2를 가진 사진 id
                related_photo2 = tag_table[tag_table['tags'] == rank2_tagname]['photo_id']
                ## 태그 rank2에 대한 연관 태그
                related_tags2 = tag_table[(tag_table['photo_id'].isin(related_photo2))&(tag_table['tags'].ne(rank1_tagname))&
                                            (tag_table['tags'].ne(rank2_tagname))&(tag_table['tags'].ne(rank3_tagname))]['tags'] #수정
                related_tags2_top2 = collections.Counter(related_tags2).most_common(2)  # 가장 많은 top2만
                ## 태그 rank2에 대한 연관 태그 2개 각각 변수로 저장
                rank2_related_tagname = [list(row)[0] for row in related_tags2_top2]
                related_tagname2_1 = rank2_related_tagname[0]
                related_tagname2_2 = rank2_related_tagname[1]

                ## 태그 rank3를 가진 사진 id
                related_photo3 = tag_table[tag_table['tags'] == rank3_tagname]['photo_id']
                ## 태그 rank3에 대한 연관 태그
                related_tags3 = tag_table[(tag_table['photo_id'].isin(related_photo3))&(tag_table['tags'].ne(rank1_tagname))&
                                            (tag_table['tags'].ne(rank2_tagname))&(tag_table['tags'].ne(rank3_tagname))]['tags'] # 수정
                related_tags3_top2 = collections.Counter(related_tags3).most_common(2)  # 가장 많은 top2만
                ## 태그 rank3에 대한 연관 태그 2개 각각 변수로 저장
                rank3_related_tagname = [list(row)[0] for row in related_tags3_top2]
                related_tagname3_1 = rank3_related_tagname[0]
                related_tagname3_2 = rank3_related_tagname[1]


                # rank1 태그의 사진 가져오기 # 수정
                photo1 = Photo.objects.filter(id__in=related_photo1).first()
                photourl = photo1.photo



                content = {
                    'rank1_tagname': rank1_tagname,  # 태그명
                    'rank2_tagname': rank2_tagname,
                    'rank3_tagname': rank3_tagname,
                    'rank1_tagfreq': rank1_tagfreq,  # 태그 빈도
                    'rank2_tagfreq': rank2_tagfreq,
                    'rank3_tagfreq': rank3_tagfreq,
                    'related_tagname1_1': related_tagname1_1,  # 연관 태그명
                    'related_tagname1_2': related_tagname1_2,
                    'related_tagname2_1': related_tagname2_1,
                    'related_tagname2_2': related_tagname2_2,
                    'related_tagname3_1': related_tagname3_1,
                    'related_tagname3_2': related_tagname3_2,
                    'photourl': photourl
                }
            else:
                content = {
                    'rank1_tagname': 'NO PHOTO',  # 태그명
                }

        else:
            # pass #리턴할 값이 없으면 오류가 나므로 리턴값을 넣어주세요(현재는 페이지만 띄워줘서 pass했습니다)
            content = {
                'rank1_tagname': 'NO PHOTO',  # 태그명
            }
        
        
        #==========================================================================
        #분석 페이지가 아니라 디테일 페이지 들어갔을 때 위치정보 저장받을 수 있도록 수정하기

        # 페이지 접속하면 위치 정보 찾아줌
        analyzed_photo_list = list(Analysis.objects.filter(user_id=user).values_list('photo_id', flat=True))
        N_anaylazed_photos = list(set(photo_id_list) - set(analyzed_photo_list))
        N_anaylazed_photo = ','.join(map(str, N_anaylazed_photos))
        if N_anaylazed_photo:
            tag_table = get_table(user, N_anaylazed_photo, 'phototag')

            # 이미 위치정보가 저장된 사진에 대해서는 위치 찾는 함수 작동X ->DB에 위치정보가 계속 저장되는 것을 막음

            if tag_table.empty == False:
                tag_table['user_id'] = user
                tag_table = search_place(tag_table)

                # 분석한 내용 db로 보내기
                lst = []
                tag_table = tag_table.drop_duplicates(['photo_id'], keep='last')
                for row in tag_table[['photo_id', 'place', 'user_id']].itertuples(index=False, name=None):
                    lst.append(row)
                tuple(lst)

                conn = pymysql.connect(host='18.223.252.140', user='python', password='python', db='mysql_db',
                                    charset='utf8')
                curs = conn.cursor(pymysql.cursors.DictCursor)
                sql = """insert into album_analysis(photo_id,location,user_id) 
                values (%s, %s, %s)"""
                curs.executemany(sql, lst)
                conn.commit()
                conn.close()
        # ==============================================================================
        return render(request, 'analysis.html', content) # 현재 월에 해당하는 분석값을 리턴 

class SearchView(APIView):
  def get(self,request):

    print('search_by_tag 함수')
    print('tag: '+tag)
    print('request.body: '+request.body)
    print('request.get: '+request.GET)
    tag=request.GET['tag']

    photo_list = []

    photo_result= PhotoTag.objects.filter(tags=tag).values_list('photo_id',flat=True)
    print(photo_result)
    for a_photo_id in photo_result:
        print(a_photo_id)
        found_photo=Photo.objects.get(id=a_photo_id)
    # print(request.user)
    # print(found_photo.author)
    # print(found_photo.id)
        if found_photo.author == request.user:
            print(found_photo.photo_id)
            photo_list.append({'url':str(found_photo.photo),'id':str(found_photo.id)})
    #   photo_id_list.append(found_photo.id)
    print(photo_list)


    print(photo_list)

    return render (request,'search.html',{'tag':tag,'photo_list' : photo_list})
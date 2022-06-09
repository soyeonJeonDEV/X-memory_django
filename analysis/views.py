import datetime
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.test import tag
from django.utils import timezone
from requests import request
from album.forms import UserForm, PhotoForm
from album.models import Photo, PhotoTag, AnalysisResult
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
#import cv2
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
import album.views



gmaps= googlemaps.Client(key='AIzaSyDlTe2iwy53wvvt8WNwJ15fgzLGNmAQpf8')

#사진 많이 찍은 위치를 지도에 표시하는 함수
def myplace(tag_table):
    if 'location' in tag_table.columns:
        place_list=tag_table['location'].str.split() #필드명 확인
        tag_table['city']=place_list.str.get(1) 
        tag_table['locality']=place_list.str.get(2)   
        placeTaken_photo=tag_table.drop_duplicates(['photo_id'])['locality'].value_counts()[0:3] #필드명 확인
        placeTaken_photo=pd.DataFrame(placeTaken_photo)
        #같은 날 찍은 사진도 카운팅 됨 #자주 방문 분석을 위해서는 create_date 추가 비교 코드 필요 
        placeTaken_photo['index']=placeTaken_photo.index
        placeTaken_photo
        places =list(placeTaken_photo.index)
        i=0
        lat = []  #위도
        lng = []  #경도
        for place in places:   
            i = i + 1
            try:
                geo_location = gmaps.geocode(place)[0].get('geometry')
                lat.append(geo_location['location']['lat'])
                lng.append(geo_location['location']['lng'])

            except:
                pass
        # 데이터프레임만들어 출력하기
        df = pd.DataFrame({'위도':lat, '경도':lng}, index=places)
        placeTaken_photo=pd.concat([df,placeTaken_photo], axis=1)
        placeTaken_photo=placeTaken_photo.rename(columns={'locality':'num'})
        placeTaken_photo
        coords = placeTaken_photo[['위도','경도']]
        coords= list(zip(coords['위도'], coords['경도']))
    
        m = folium.Map(
            location=(35.95,128.25),
            zoom_start=7
        )
        for i in range(3):
            folium.Marker(coords[i],
                    popup=str(placeTaken_photo['num'][i])+'개의 사진을 찍었어요!',
                    tootip='나의'+str(i+1)+'순위 방문지').add_to(m)
        maps=m._repr_html_() 
    else: 
        m = folium.Map(
            location=(35.95,128.25),
            zoom_start=7
        )
        maps=m._repr_html_()

    return maps

def analysisPlace(request):
    user = get_user_model()
    photo_id_list=list(Photo.objects.filter(author_id=request.user.id).values_list('id', flat=True))
    photo_id=','.join(map(str, photo_id_list))
  
    tag_table= get_table(user,photo_id,'phototag') #여기에 place열 있어야함
    analysisresult_tb= get_table(user,photo_id,'analysisresult')
    if analysisresult_tb.empty == False:
        tag_table=pd.merge(tag_table,analysisresult_tb, how='left', left_on='photo_id', right_on='photo_id')

    
    maps = myplace(tag_table)
    return render(request, 'analysisPlace.html',{'map' : maps})


# 요일별 태그 분석 함수
def weekday_tag(tag_table):
  tag_table['create_date']=pd.to_datetime(tag_table['create_date'])
  tag_table['weekday']=tag_table['create_date'].dt.weekday

  weekday_tag=pd.DataFrame(columns={'tags',0,'weekday'})
  for i in range(7):
      weekday=tag_table[tag_table['weekday'] == i].groupby('tags').size()
      # weekday=weekday.to_frame() 전체 요일별 태그
      weekday=weekday[weekday==max(weekday)].to_frame() #요일별 가장 많은 태그
      weekday=weekday.reset_index()
      weekday['weekday']=i
      weekday_tag=pd.concat([weekday_tag, weekday])
  weekday_tag=weekday_tag.rename(columns={0:'num'})
  weekday={'mon':0,'tue':1,'wed':2,'thu':3,'fri':4,'sat':5,'sun':6}
  weekday=dict((value,key) for (key, value) in weekday.items())
  list(map(lambda x:weekday.get(x),list(weekday_tag['weekday'])))
  weekday_tag['weekday']=list(map(lambda x:weekday.get(x),list(weekday_tag['weekday'])))

  font_path = "C:/Windows/Fonts/NGULIM.TTF"
  font = font_manager.FontProperties(fname=font_path).get_name()
  rc('font', family=font)

  bar = plt.bar(weekday_tag['weekday'],weekday_tag['num'],color=sns.color_palette('hls'))
  plt.title('요일별 BEST 태그')
  for i in range(7):
      plt.text(list(map(lambda x: x.get_x(), bar))[i]+ list(map(lambda x: x.get_width()/2.0, bar))[i],
              list(map(lambda x: x.get_height(), bar))[i],
              list(weekday_tag['tags'])[i],
              ha='center', va='bottom', size = 12)

  plt.savefig('C:\X-travel-django\X-travel-django\static\images\weekday_graph.png')
  #이미지 저장 경로 수정 필요(db에 user.id와 같이 업로드)


  
#photo_id 참조하여 DB에서 정보 가져오는 함수 
#================================================================================
"""
  user = get_user_model()
  photo_id_list=list(Photo.objects.filter(author_id=request.user.id).values_list('id', flat=True))
  photo_id=','.join(map(str, photo_id_list))

"""
#함수 쓸 때 위에 있어야 하는 문장 사용:get_table(user,photo_id, 가져오고자 하는 테이블명)
# DBtable: 'analysisresult', 'photo', 'phototag
def get_table(user,photo_id,DBtable):
  # MySQL Connection 연결하고 테이블에서 데이터 가져옴
  conn = pymysql.connect(host='18.219.244.45', user='python', password='python',db='mysql_db', charset='utf8')
  curs = conn.cursor(pymysql.cursors.DictCursor)
  sql = 'select * from album_' + DBtable + ' where photo_id in (' + photo_id +')'
  curs.execute(sql)
  rows = curs.fetchall()
  table = pd.DataFrame(rows)
  return table
#=============================================================================================

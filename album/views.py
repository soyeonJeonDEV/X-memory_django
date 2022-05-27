
# Create your views here.
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from .forms import UserForm, PhotoForm
from .models import Photo

@login_required(login_url='login')
def index(request):
  """
  album
  """
  # 조회
  user = get_user_model()

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

      # # 리스트로 입력된 icons를 스트링으로 변환해서 필드에 넣어줌
      # icons = request.POST.getlist('icons[]')
      # post.icons='&'.join(icons)
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

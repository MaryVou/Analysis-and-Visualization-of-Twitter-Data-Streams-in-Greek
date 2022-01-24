from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('ajax/getTweets', views.getTweets, name='getTweets')
]
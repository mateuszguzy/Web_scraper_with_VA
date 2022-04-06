from django.urls import path
from . import views


app_name = "website_form"
urlpatterns = [
    path('', views.index, name="index"),
    path('results/', views.results, name="results")
]

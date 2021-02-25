 
from django.contrib import admin
from django.urls import path 
from techposts import views 
from .views import ModelList # this is for the new class-based view 
from techposts.models import AllPosts

urlpatterns = [
 
  path("admin/", admin.site.urls),  # Activates the admin interface 
  path('', views.home, name='home'),     
  path('error', views.errors_view),     
  path('get-and-store', views.get_and_store_view),    
  path('scrapecontents', views.scrapecontents_view),
  path('modelsearch', views.modelsearch_view),
  path('retrieve-recipes-classbased', ModelList.as_view(model=AllPosts)), 
  
]

 

from django.urls import path
from . import views
from projects.views import employee_projects

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('<int:project_id>/', views.project_detail, name='project_detail'),
    path('<int:employee_id>/projects/',employee_projects,name='employee_projects'),
]

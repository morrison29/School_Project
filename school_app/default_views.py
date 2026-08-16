from django.shortcuts import render
from .views.auth_views import *
from .views.admin_views import *
from .views.teacher_views import *
from .views.student_views import *
from .views.class_arm_views import *
from .views.subject_views import *
from .views.assignment_views import *
from .views.result_views import *
from .views.lists import *

def home(request):
    return render(request, 'school/home.html')



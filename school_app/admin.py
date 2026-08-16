from django.contrib import admin
from .models import StudentProfile, TeacherProfile, Subject, MidtermAssignment, Result, EmailOTP, ClassArm, AdminProfile
# Register your models here.

admin.site.register(StudentProfile)
admin.site.register(TeacherProfile)
admin.site.register(Subject)
admin.site.register(Result)
admin.site.register(MidtermAssignment)
admin.site.register(ClassArm)
admin.site.register(AdminProfile)
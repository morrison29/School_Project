from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from school_app.decorators import admin_or_teacher_required
from school_app.models import TeacherProfile, StudentProfile
from django.views.decorators.http import require_POST
from school_app.decorators import admin_required, admin_or_teacher_required


@admin_or_teacher_required
def view_teachers(request):
    teachers = TeacherProfile.objects.all()
    teachers_class = teachers.filter(class_arm__isnull=False)
    return render(request, 'school/view_teachers.html', {'teachers': teachers, 'teachers_class': teachers_class})


@admin_or_teacher_required
def view_students(request):
    students = StudentProfile.objects.all()
    students_class = students.filter(class_arm__isnull=False)
    return render(request, 'school/view_students.html', {'students': students, 'students_class': students_class})


@admin_required
@require_POST
def delete_teacher(request, teacher_id):
    teacher = get_object_or_404(TeacherProfile, id=teacher_id)
    teacher.user.delete()
    messages.success(request, "Teacher deleted successfully.")
    return redirect('school_app:view_teachers')


@admin_required
@require_POST
def delete_student(request, student_id):
    student = get_object_or_404(StudentProfile, id=student_id)
    student.user.delete()
    messages.success(request, "Student deleted successfully.")
    return redirect('school_app:view_students')
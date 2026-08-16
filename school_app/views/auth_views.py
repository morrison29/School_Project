from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from Mini_School_Sysytem import settings
from school_app.utils import generate_otp
from school_app.decorators import admin_required, teacher_required, student_required, admin_or_teacher_required
from school_app.models import TeacherProfile, StudentProfile, EmailOTP


TEACHERS_GROUP = 'Teachers'
STUDENT_GROUP = 'Students'

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.is_superuser:
                return redirect('school_app:admin-dashboard')
            elif user.groups.filter(name=TEACHERS_GROUP).exists():
                return redirect('school_app:teacher-dashboard')
            elif user.groups.filter(name=STUDENT_GROUP).exists():
                return redirect('school_app:student-dashboard')
            messages.error(request, "User has no assigned role.")
            return redirect('school_app:login')

        messages.error(request, "Invalid username or password.")
        return redirect('school_app:login')

    return render(request, 'school/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('school_app:home')


@admin_required
def register_teacher(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not all([first_name, last_name, username, email, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return redirect('school_app:register_teacher')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('school_app:register_teacher')

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('school_app:register_teacher')

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('school_app:register_teacher')

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    is_active=True,
                    first_name=first_name,
                    last_name=last_name,
                )
                teacher_group = Group.objects.get(name=TEACHERS_GROUP)
                user.groups.add(teacher_group)
                TeacherProfile.objects.create(user=user)

        except Group.DoesNotExist:
            messages.error(request, "Teacher group is not configured. Contact the system administrator.")
            return redirect('school_app:register_teacher')
        
        messages.success(request, "Tecaher Registered Successfully")
        return redirect('school_app:view_teachers')

    return render(request, 'school/register_teacher.html')


@teacher_required
def complete_teacher_registration(request):
    profile = get_object_or_404(TeacherProfile, user=request.user)

    if request.method == 'POST':
        profile.phone_number = request.POST.get('phone_number', '')
        profile.address = request.POST.get('address', '')
        profile.save()

        messages.success(request, "Profile completed.")
        return redirect('school_app:teacher-dashboard')

    return render(request, 'school/complete_teacher_registration.html')


@admin_required
def register_student(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        student_email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not all([first_name, last_name, username, student_email, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return redirect('school_app:register_student')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('school_app:register_student')

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('school_app:register_student')

        if User.objects.filter(email__iexact=student_email).exists():
            messages.error(request, "Email already exists.")
            return redirect('school_app:register_student')

        try:
            with transaction.atomic():
                student = User.objects.create_user(
                    first_name=first_name,
                    last_name=last_name,
                    username=username,
                    email=student_email,
                    password=password,
                    is_active=True,
                )
                student_group = Group.objects.get(name=STUDENT_GROUP)
                student.groups.add(student_group)
                StudentProfile.objects.create(user=student)

        except Group.DoesNotExist:
            messages.error(request, "Student group is not configured. Contact the system administrator.")
            return redirect('school_app:register_student')

        messages.success(
            request, "Student account created"
        )
        return redirect('school_app:view_students')
    return render(request, 'school/register_student.html')

 
@admin_or_teacher_required
def assign_registration_number(request, student_id):

    student = get_object_or_404(StudentProfile, id=student_id)
 
    if request.method == 'POST':
        reg_number = request.POST.get('registration_number', '').strip()
 
        if not reg_number:
            messages.error(request, "Registration number is required.")
            return redirect('school_app:assign_registration_number',
                            student_id=student_id)
 
        
        if (StudentProfile.objects
                .filter(registration_number=reg_number)
                .exclude(id=student_id)
                .exists()):
            messages.error(
                request,
                "That registration number is already assigned to "
                "another student.",
            )
            return redirect('school_app:assign_registration_number',
                            student_id=student_id)
 
        student.registration_number = reg_number
        student.save()
        messages.success(
            request,
            f"Registration number assigned to "
            f"{student.user.get_full_name()}.",
        )
        return redirect('school_app:view_students')
 
    return render(request, 'school/assign_registration_number.html',
                  {'student': student})


@student_required
def complete_student_registration(request):
    profile = get_object_or_404(StudentProfile, user=request.user)

    if request.method == 'POST':
        profile.date_of_birth = request.POST.get('date_of_birth')
        profile.address = request.POST.get('address', '')
        profile.phone_number = request.POST.get('phone_number', '')
        profile.save()

        messages.success(request, "Profile completed.")
        return redirect('school_app:student-dashboard')

    return render(request, 'school/complete_student_registration.html')

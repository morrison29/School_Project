from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from school_app.models import StudentProfile, TeacherProfile, Result, ClassArm
from school_app.decorators import student_required



@student_required
def student_dashboard(request):
    student = get_object_or_404(StudentProfile, user=request.user)
    class_arm = student.class_arm
    teacher = TeacherProfile.objects.filter(class_arm=class_arm).first() if class_arm else None
    return render(request, 'school/student_dashboard.html', {
        'student': student,
        'class_arm': class_arm,
        'teacher': teacher,
    })


@student_required
def student_profile(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    return render(request, 'school/student_profile.html', {'profile': profile})


@student_required
def edit_student_profile(request):
    profile = get_object_or_404(StudentProfile, user=request.user)

    if request.method == "POST":
        profile.address = request.POST.get('address', '')
        profile.phone_number = request.POST.get('phone_number', '')
        profile.save()

        messages.success(request, "Profile updated successfully.")
        return redirect('school_app:student_profile')

    return render(request, 'school/edit_student_profile.html', {'profile': profile})

@student_required
def student_results(request):
    student = get_object_or_404(StudentProfile, user=request.user)
    results = Result.objects.filter(student=student)
    return render(request, 'school/student_results.html', {'results': results})

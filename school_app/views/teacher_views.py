from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from school_app.models import TeacherProfile, StudentProfile
from school_app.decorators import teacher_required
from school_app.models import ClassArm, Subject

@teacher_required
def teacher_dashboard(request):
    context = {
        'students_count':   ClassArm.objects.count(),
        'subjects_count':   Subject.objects.count(),
        
    }
    return render(request, 'school/teacher_dashboard.html', context)


@teacher_required
def teacher_profile(request):
    profile = get_object_or_404(TeacherProfile, user=request.user)
    return render(request, 'school/teacher_profile.html', {'profile': profile})


@teacher_required
def edit_teacher_profile(request):
    profile = get_object_or_404(TeacherProfile, user=request.user)

    if request.method == "POST":
        profile.address = request.POST.get('address', '')
        profile.phone_number = request.POST.get('phone_number', '')
        profile.save()

        messages.success(request, "Profile updated successfully.")
        return redirect('school_app:teacher_profile')

    return render(request, 'school/edit_teacher_profile.html', {'profile': profile})

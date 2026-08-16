from django.shortcuts import render, redirect, get_object_or_404
from school_app.models import Subject, ClassArm
from django.contrib import messages
from school_app.decorators import admin_required, teacher_required, student_required, admin_or_teacher_required
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@admin_required
def register_subjects(request):
    if request.method == "POST":
        subject_name = request.POST.get('subject_name', '').strip()

        if not subject_name:
            messages.error(request, "Subject name is required.")
            return redirect('school_app:register_subjects')

        if Subject.objects.filter(subject_name__iexact=subject_name).exists():
            messages.error(request, "Subject already exists.")
            return redirect('school_app:register_subjects')

        Subject.objects.create(subject_name=subject_name)
        messages.success(request, "Subject registered successfully.")
        return redirect('school_app:view_all_subjects')

    return render(request, 'school/subjects.html', {'subjects': Subject.objects.all()})


@login_required
def view_all_subjects(request):
    subjects = Subject.objects.all()
    return render(request, 'school/view_all_subjects.html', {'subjects': subjects})


@admin_required
@require_POST
def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    subject.delete()
    messages.success(request, "Subject deleted successfully.")
    return redirect('school_app:view_all_subjects')


@admin_required
def assign_class_subject(request):
    if request.method == "POST":
        class_arm_id = request.POST.get('class_arm')
        subject_ids = request.POST.getlist('subject')

        if not class_arm_id:
            messages.error(request, "Please select a class arm.")
            return redirect('school_app:assign_class_subject')

        class_arm = get_object_or_404(ClassArm, id=class_arm_id)
        subjects = Subject.objects.filter(id__in=subject_ids)

        if not subjects.exists():
            messages.error(request, "Please select at least one valid subject.")
            return redirect('school_app:assign_class_subject')

        class_arm.subjects.set(subjects)
        messages.success(request, "Subjects assigned successfully.")
        return redirect('school_app:assign_class_subject')

    return render(request, 'school/assign_class_subject.html', {
        'class_arms': ClassArm.objects.all(),
        'subjects': Subject.objects.all(),
    })


@login_required
def view_class_subjects(request, class_arm_id):
    class_arm = get_object_or_404(ClassArm, id=class_arm_id)
    subjects = class_arm.subjects.all()
    return render(request, 'school/view_class_subjects.html', {'class_arm': class_arm, 'subjects': subjects})

import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from school_app.models import MidtermAssignment, TeacherProfile, StudentProfile, ClassArm, Subject
from school_app.decorators import admin_required, teacher_required, student_required, admin_or_teacher_required


@teacher_required
def create_midterm_assignment(request):
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
    class_arm = teacher_profile.class_arm

    if class_arm is None:
        messages.error(request, "You are not assigned to a class arm yet.")
        return redirect('school_app:teacher-dashboard')

    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        subject_id = request.POST.get('subject')
        due_date = request.POST.get('due_date')
        attachment = request.FILES.get('attachment')

        if not all([title, description, subject_id, due_date]):
            messages.error(request, "All fields are required.")
            return redirect('school_app:create_midterm_assignment')

        subject = get_object_or_404(Subject, id=subject_id)

        if subject not in class_arm.subjects.all():
            messages.error(request, "Selected subject is not assigned to your class arm.")
            return redirect('school_app:create_midterm_assignment')

        if attachment:
            ext = attachment.name.rsplit('.', 1)[-1].lower() if '.' in attachment.name else ''
            if ext not in ('pdf', 'doc', 'docx'):
                messages.error(request, "Attachment must be a PDF or Word document (.pdf, .doc, .docx).")
                return redirect('school_app:create_midterm_assignment')
            max_size = 10 * 1024 * 1024  # 10MB
            if attachment.size > max_size:
                messages.error(request, "Attachment must be under 10MB.")
                return redirect('school_app:create_midterm_assignment')

        MidtermAssignment.objects.create(
            title=title,
            description=description,
            subject=subject,
            class_arm=class_arm,
            due_date=due_date,
            attachment=attachment,
        )
        messages.success(request, "Midterm assignment created successfully.")
        return redirect('school_app:teacher-dashboard')

    # Only show subjects actually assigned to this teacher's class arm,
    # otherwise the form lets the teacher pick a subject that will always
    # fail the validation above.
    return render(request, 'school/create_midterm_assignment.html', {'subjects': class_arm.subjects.all()})


@login_required
def view_midterm_assignments(request, class_arm_id):
    class_arm = get_object_or_404(ClassArm, id=class_arm_id)

    is_admin = request.user.is_superuser
    is_class_teacher = TeacherProfile.objects.filter(user=request.user, class_arm=class_arm).exists()
    is_class_student = StudentProfile.objects.filter(user=request.user, class_arm=class_arm).exists()

    if not (is_admin or is_class_teacher or is_class_student):
        messages.error(request, "You do not have permission to view these assignments.")
        return redirect('school_app:login')

    assignments = MidtermAssignment.objects.filter(class_arm=class_arm)
    return render(request, 'school/view_midterm_assignments.html', {'class_arm': class_arm, 'assignments': assignments})


@student_required
def my_assignments(request):
    """Student-facing 'Assignments' link — scoped to their own class arm only."""
    profile = getattr(request.user, 'studentprofile', None)
    class_arm = profile.class_arm if profile else None
    assignments = MidtermAssignment.objects.filter(class_arm=class_arm) if class_arm else None
    return render(request, 'school/view_midterm_assignments.html', {'class_arm': class_arm, 'assignments': assignments})


@login_required
def view_each_midterm_assignment(request, assignment_id):
    assignment = get_object_or_404(MidtermAssignment, id=assignment_id)
    class_arm = assignment.class_arm

    is_admin = request.user.is_superuser
    is_class_teacher = TeacherProfile.objects.filter(user=request.user, class_arm=class_arm).exists()
    is_class_student = StudentProfile.objects.filter(user=request.user, class_arm=class_arm).exists()

    if not (is_admin or is_class_teacher or is_class_student):
        messages.error(request, "You do not have permission to view this assignment.")
        return redirect('school_app:login')

    return render(request, 'school/view_each_midterm_assignment.html', {
        'assignment': assignment,
        'attachment_filename': os.path.basename(assignment.attachment.name) if assignment.attachment else None,
    })


@teacher_required
@require_POST
def delete_midterm_assignment(request, assignment_id):
    assignment = get_object_or_404(MidtermAssignment, id=assignment_id)
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)

    if assignment.class_arm != teacher_profile.class_arm:
        messages.error(request, "You do not have permission to delete this assignment.")
        return redirect('school_app:teacher-dashboard')

    class_arm_id = assignment.class_arm.id
    assignment.delete()
    messages.success(request, "Midterm assignment deleted successfully.")
    # NOTE: double-check this URL name against urls.py — the original code
    # redirected to 'view_midterm_assignment' (singular) even though the
    # corresponding view function is named view_midterm_assignments
    # (plural). Keeping the original name here; rename if urls.py disagrees.
    return redirect('school_app:view_midterm_assignments', class_arm_id=class_arm_id)
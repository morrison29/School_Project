from django.shortcuts import render, redirect
from django.contrib import messages
from school_app.decorators import admin_required, teacher_required, student_required, admin_or_teacher_required
from school_app.models import TeacherProfile, StudentProfile, ClassArm, Subject, AcademicSession, Term
from school_app.utils import get_current_term, get_current_session



@admin_required
def admin_dashboard(request):
    context = {
        'teachers_count':   TeacherProfile.objects.count(),
        'students_count':   StudentProfile.objects.count(),
        'class_arms_count': ClassArm.objects.count(),
        'subjects_count':   Subject.objects.count(),
        'current_term': get_current_term(),
    }
    return render(request, 'school/admin_dashboard.html', context)
   

@admin_required
def admin_profile(request):
    return render(request, 'school/admin_profile.html', {'user_obj': request.user})


@admin_required
def edit_admin_profile(request):
    if request.method == "POST":
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()

        messages.success(request, "Profile updated successfully.")
        return redirect('school_app:admin_profile')

    return render(request, 'school/edit_admin_profile.html', {'user_obj': request.user})

@admin_required
def start_new_term(request):
    sessions = AcademicSession.objects.all()
    current_term = get_current_term()

    if request.method == "POST":
        session_name = request.POST.get('session_name', '').strip()
        term_name = request.POST.get('term_name')

        if not session_name or term_name not in dict(Term.TERM_CHOICES):
            messages.error(request, "Please provide a valid session and term.")
            return redirect('school_app:start_new_term')

        session, _ = AcademicSession.objects.get_or_create(name=session_name)
        AcademicSession.objects.exclude(id=session.id).update(is_current=False)
        session.is_current = True
        session.save()

        term, _ = Term.objects.get_or_create(session=session, name=term_name)
        Term.objects.exclude(id=term.id).update(is_current=False)
        term.is_current = True
        term.save()

        messages.success(request, f"{term} is now the active term.")
        return redirect('school_app:admin-dashboard')

    return render(request, 'school/start_new_term.html', {
        'sessions': sessions,
        'current_term': current_term,
    })
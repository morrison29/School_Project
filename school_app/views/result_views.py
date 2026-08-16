from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from school_app.models import Term, AcademicSession
from django.contrib import messages
from school_app.decorators import admin_or_teacher_required, teacher_required, admin_required, student_required
from school_app.models import Result, StudentProfile, TeacherProfile, ClassArm, Subject
from school_app.utils import calculate_total_score, calculate_grade, compute_positions, generate_comment, get_current_session, get_current_term
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.http import HttpResponse


def compute_positions(class_arm, subject, term):
    results = Result.objects.filter(class_arm=class_arm, subject=subject, term=term).order_by('-total_score')
    for position, result in enumerate(results, start=1):
        result.position = position
        result.save()


def calculate_class_position(class_arm, term):
    students = StudentProfile.objects.filter(class_arm=class_arm)
    averages = []
    for s in students:
        results = Result.objects.filter(student=s, class_arm=class_arm, term=term)
        total = results.count()
        avg = round(sum(r.total_score for r in results) / total, 1) if total else 0
        averages.append((s.id, avg))
    averages.sort(key=lambda x: x[1], reverse=True)
    return {student_id: pos for pos, (student_id, avg) in enumerate(averages, start=1)}


@admin_required
def admin_view_results(request):
    class_arms = ClassArm.objects.all()
    terms = Term.objects.select_related('session').order_by('-session__name', 'name')
    selected_arm = None
    student_results_map = []

    term_id = request.GET.get('term')
    selected_term = get_object_or_404(Term, id=term_id) if term_id else get_current_term()

    class_arm_id = request.GET.get('class_arm')
    if class_arm_id and selected_term:
        selected_arm = get_object_or_404(ClassArm, id=class_arm_id)
        students = (
            StudentProfile.objects
            .filter(class_arm=selected_arm)
            .select_related('user')
            .order_by('user__last_name', 'user__first_name')
        )
        for student in students:
            results = (
                Result.objects
                .filter(student=student, class_arm=selected_arm, term=selected_term)
                .select_related('subject')
                .order_by('subject__subject_name')
            )
            student_results_map.append((student, results))

    return render(request, 'school/admin_view_results.html', {
        'class_arms': class_arms,
        'terms': terms,
        'selected_arm': selected_arm,
        'selected_term': selected_term,
        'student_results_map': student_results_map,
    })



@teacher_required
def enter_scores(request, class_arm_id):
    class_arm = get_object_or_404(ClassArm, id=class_arm_id)
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)

    if class_arm != teacher_profile.class_arm:
        messages.error(request, "You can only enter scores for your own class arm.")
        return redirect('school_app:teacher-dashboard')

    students = (
        StudentProfile.objects
        .filter(class_arm=class_arm)
        .select_related('user')
        .order_by('user__last_name', 'user__first_name')
    )
    return render(request, 'school/enter_scores.html', {
        'class_arm': class_arm,
        'students':  students,
    })

@teacher_required
def enter_student_scores(request, student_id):
    student = get_object_or_404(StudentProfile, id=student_id)
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)

    if student.class_arm != teacher_profile.class_arm:
        messages.error(request, "You can only enter scores for students in your own class arm.")
        return redirect('school_app:teacher-dashboard')

    current_term = get_current_term()
    if not current_term:
        messages.error(request, "No active term set. Ask an admin to start a term first.")
        return redirect('school_app:teacher-dashboard')

    class_arm = student.class_arm
    subjects = class_arm.subjects.all().order_by('subject_name')

    existing = {
        r.subject_id: r
        for r in Result.objects.filter(student=student, class_arm=class_arm, term=current_term)
    }

    if request.method == "POST":
        for subject in subjects:
            test_score = request.POST.get(f'test_{subject.id}', 0) or 0
            assignment_score = request.POST.get(f'assignment_{subject.id}', 0) or 0
            exam_score = request.POST.get(f'exam_{subject.id}', 0) or 0

            total = calculate_total_score(
                float(test_score), float(assignment_score), float(exam_score)
            )
            grade = calculate_grade(total)

            Result.objects.update_or_create(
                student=student,
                subject=subject,
                class_arm=class_arm,
                term=current_term,
                defaults={
                    'session': current_term.session,
                    'test_score': test_score,
                    'assignment_score': assignment_score,
                    'exam_score': exam_score,
                    'total_score': total,
                    'grade': grade,
                },
            )
        for subject in subjects:
            compute_positions(class_arm, subject, current_term)

        messages.success(request, f"Scores saved for {student.user.get_full_name()}.")
        return redirect('school_app:enter_scores', class_arm_id=class_arm.id)

    return render(request, 'school/enter_student_scores.html', {
        'student': student,
        'subjects': subjects,
        'existing': existing,
        'class_arm': class_arm,
        'current_term': current_term,
    })
@student_required
def download_student_results_pdf(request):
    student = get_object_or_404(StudentProfile, user=request.user)

    term_id = request.GET.get('term')
    selected_term = get_object_or_404(Term, id=term_id) if term_id else get_current_term()

    if not selected_term:
        messages.error(request, "No active term set yet.")
        return redirect('school_app:student-results')

    results = (
        Result.objects
        .filter(student=student, term=selected_term)
        .select_related('subject', 'class_arm')
        .order_by('subject__subject_name')
    )
    total_subjects = results.count()
    overall_average = (
        round(sum(r.total_score for r in results) / total_subjects, 1)
        if total_subjects else 0
    )
    class_position = None
    if student.class_arm:
        class_position = calculate_class_position(student.class_arm, selected_term).get(student.id)
    comment = generate_comment(overall_average)

    response = HttpResponse(content_type='application/pdf')
    filename = f"{student.user.get_full_name().replace(' ', '_')}_{selected_term.name}_results.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    doc = SimpleDocTemplate(response, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(f"Academic Result Sheet — {selected_term}", styles['Title']))
    story.append(Spacer(1, 12))

    info_data = [
        ["Name:", student.user.get_full_name(), "Average:", str(overall_average)],
        ["Class:", student.class_arm.name if student.class_arm else "—",
         "Position in Class:", str(class_position) if class_position else "—"],
    ]
    info_table = Table(info_data, colWidths=[3*cm, 5*cm, 4*cm, 3*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))

    table_data = [["Subject", "Test", "Assignment", "Exam", "Total", "Grade", "Position"]]
    for r in results:
        table_data.append([
            r.subject.subject_name, r.test_score, r.assignment_score,
            r.exam_score, r.total_score, r.grade, r.position or "—",
        ])
    results_table = Table(table_data, colWidths=[4.5*cm, 2*cm, 2.7*cm, 2*cm, 2*cm, 2*cm, 2*cm])
    results_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fc')]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(results_table)
    story.append(Spacer(1, 24))

    comment_style = ParagraphStyle('Comment', parent=styles['Normal'], fontSize=11, leading=15)
    story.append(Paragraph("<b>Teacher's Comment:</b>", styles['Heading3']))
    story.append(Paragraph(f'"{comment}"', comment_style))

    doc.build(story)
    return response

@admin_required
def view_student_results_as_admin(request, student_id):
    student = get_object_or_404(StudentProfile, id=student_id)

    term_id = request.GET.get('term')
    selected_term = get_object_or_404(Term, id=term_id) if term_id else get_current_term()

    results = Result.objects.filter(student=student, term=selected_term) if selected_term else Result.objects.none()
    all_terms = (
        Term.objects.filter(results__student=student)
        .distinct().select_related('session').order_by('-session__name', 'name')
    )

    return render(request, 'school/view_student_results_as_admin.html', {
        'student': student,
        'results': results,
        'selected_term': selected_term,
        'all_terms': all_terms,
    })
@student_required
def student_results(request):
    student = get_object_or_404(StudentProfile, user=request.user)

    term_id = request.GET.get('term')
    selected_term = get_object_or_404(Term, id=term_id) if term_id else get_current_term()

    all_terms = (
        Term.objects.filter(results__student=student)
        .distinct().select_related('session').order_by('-session__name', 'name')
    )

    if not selected_term:
        return render(request, 'school/student_results.html', {
            'student': student, 'results': [], 'total_subjects': 0,
            'overall_average': 0, 'class_position': None, 'comment': None,
            'selected_term': None, 'all_terms': all_terms,
        })

    results = (
        Result.objects
        .filter(student=student, term=selected_term)
        .select_related('subject', 'class_arm')
        .order_by('subject__subject_name')
    )
    total_subjects = results.count()
    overall_average = (
        round(sum(r.total_score for r in results) / total_subjects, 1)
        if total_subjects else 0
    )
    class_position = None
    if student.class_arm:
        class_position = calculate_class_position(student.class_arm, selected_term).get(student.id)
    comment = generate_comment(overall_average)

    return render(request, 'school/student_results.html', {
        'results': results, 'student': student, 'total_subjects': total_subjects,
        'overall_average': overall_average, 'class_position': class_position,
        'comment': comment, 'selected_term': selected_term, 'all_terms': all_terms,
    })

@teacher_required
def view_student_results_as_teacher(request, student_id):
    student = get_object_or_404(StudentProfile, id=student_id)
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)

    if student.class_arm != teacher_profile.class_arm:
        messages.error(request, "You can only view results for students in your own class arm.")
        return redirect('school_app:teacher-dashboard')

    term_id = request.GET.get('term')
    selected_term = get_object_or_404(Term, id=term_id) if term_id else get_current_term()

    results = Result.objects.filter(student=student, term=selected_term) if selected_term else Result.objects.none()
    all_terms = (
        Term.objects.filter(results__student=student)
        .distinct().select_related('session').order_by('-session__name', 'name')
    )

    return render(request, 'school/view_student_results_as_teacher.html', {
        'student': student,
        'results': results,
        'selected_term': selected_term,
        'all_terms': all_terms,
    })
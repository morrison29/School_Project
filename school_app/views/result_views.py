import csv
import io
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
def download_scores_csv_template(request, class_arm_id):
    class_arm = get_object_or_404(ClassArm, id=class_arm_id)
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)

    if class_arm != teacher_profile.class_arm:
        messages.error(request, "You can only download the template for your own class arm.")
        return redirect('school_app:teacher-dashboard')

    current_term = get_current_term()
    students = StudentProfile.objects.filter(class_arm=class_arm).select_related('user').order_by('user__last_name', 'user__first_name')
    subjects = class_arm.subjects.all().order_by('subject_name')

    existing = {}
    if current_term:
        for r in Result.objects.filter(class_arm=class_arm, term=current_term):
            existing[(r.student_id, r.subject_id)] = r

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{class_arm.name}_scores_template.csv"'
    writer = csv.writer(response)
    writer.writerow(['username', 'subject', 'test', 'assignment', 'exam'])
    for student in students:
        for subject in subjects:
            existing_result = existing.get((student.id, subject.id))
            writer.writerow([
                student.user.username,
                subject.subject_name,
                existing_result.test_score if existing_result else '',
                existing_result.assignment_score if existing_result else '',
                existing_result.exam_score if existing_result else '',
            ])
    return response


@teacher_required
def import_scores_csv(request, class_arm_id):
    class_arm = get_object_or_404(ClassArm, id=class_arm_id)
    teacher_profile = get_object_or_404(TeacherProfile, user=request.user)

    if class_arm != teacher_profile.class_arm:
        messages.error(request, "You can only import scores for your own class arm.")
        return redirect('school_app:teacher-dashboard')

    current_term = get_current_term()
    if not current_term:
        messages.error(request, "No active term set. Ask an admin to start a term first.")
        return redirect('school_app:teacher-dashboard')

    import_errors = []
    success_count = 0

    if request.method == "POST":
        csv_file = request.FILES.get('csv_file')

        if not csv_file:
            import_errors.append("No file was uploaded.")
        elif not csv_file.name.lower().endswith('.csv'):
            import_errors.append("File must be a .csv file.")
        elif csv_file.size > 2 * 1024 * 1024:
            import_errors.append("File is too large (2MB max).")
        else:
            try:
                decoded = csv_file.read().decode('utf-8-sig')
            except UnicodeDecodeError:
                import_errors.append("Could not read the file — make sure it's saved as CSV (UTF-8).")
                decoded = None

            if decoded is not None:
                reader = csv.DictReader(io.StringIO(decoded))
                required_cols = {'username', 'subject', 'test', 'assignment', 'exam'}
                if not reader.fieldnames or not required_cols.issubset({c.strip().lower() for c in reader.fieldnames}):
                    import_errors.append(
                        "CSV header must include: username, subject, test, assignment, exam. "
                        "Use the downloadable template to avoid formatting issues."
                    )
                else:
                    # Normalize header lookups so column order / case doesn't matter.
                    field_map = {c.strip().lower(): c for c in reader.fieldnames}
                    students_by_username = {
                        s.user.username.lower(): s
                        for s in StudentProfile.objects.filter(class_arm=class_arm).select_related('user')
                    }
                    subjects_by_name = {s.subject_name.lower(): s for s in class_arm.subjects.all()}
                    touched_subjects = {}

                    for row_num, row in enumerate(reader, start=2):  # header is row 1
                        username = (row.get(field_map['username']) or '').strip()
                        subject_name = (row.get(field_map['subject']) or '').strip()

                        if not username or not subject_name:
                            import_errors.append(f"Row {row_num}: username and subject are required.")
                            continue

                        student = students_by_username.get(username.lower())
                        if not student:
                            import_errors.append(f"Row {row_num}: '{username}' is not a student in {class_arm.name}.")
                            continue

                        subject = subjects_by_name.get(subject_name.lower())
                        if not subject:
                            import_errors.append(f"Row {row_num}: '{subject_name}' is not assigned to {class_arm.name}.")
                            continue

                        try:
                            test = float(row.get(field_map['test']) or 0)
                            assignment = float(row.get(field_map['assignment']) or 0)
                            exam = float(row.get(field_map['exam']) or 0)
                        except ValueError:
                            import_errors.append(f"Row {row_num}: scores must be numbers.")
                            continue

                        if not (0 <= test <= 20):
                            import_errors.append(f"Row {row_num}: test score must be between 0 and 20.")
                            continue
                        if not (0 <= assignment <= 10):
                            import_errors.append(f"Row {row_num}: assignment score must be between 0 and 10.")
                            continue
                        if not (0 <= exam <= 70):
                            import_errors.append(f"Row {row_num}: exam score must be between 0 and 70.")
                            continue

                        total = calculate_total_score(test, assignment, exam)
                        grade = calculate_grade(total)

                        Result.objects.update_or_create(
                            student=student,
                            subject=subject,
                            class_arm=class_arm,
                            term=current_term,
                            defaults={
                                'session': current_term.session,
                                'test_score': test,
                                'assignment_score': assignment,
                                'exam_score': exam,
                                'total_score': total,
                                'grade': grade,
                            },
                        )
                        touched_subjects[subject.id] = subject
                        success_count += 1

                    for subject in touched_subjects.values():
                        compute_positions(class_arm, subject, current_term)

        if success_count and not import_errors:
            messages.success(request, f"Imported {success_count} score{'s' if success_count != 1 else ''} successfully.")
            return redirect('school_app:enter_scores', class_arm_id=class_arm.id)

    return render(request, 'school/import_scores_csv.html', {
        'class_arm': class_arm,
        'import_errors': import_errors,
        'success_count': success_count,
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
        return redirect('school_app:enter_student_scores', student_id=student.id)

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

    total_subjects = results.count()
    overall_average = (
        round(sum(r.total_score for r in results) / total_subjects, 1)
        if total_subjects else 0
    )
    class_position = None
    if student.class_arm and selected_term:
        class_position = calculate_class_position(student.class_arm, selected_term).get(student.id)
    comment = generate_comment(overall_average) if total_subjects else None

    return render(request, 'school/view_student_results_as_admin.html', {
        'student': student,
        'results': results,
        'selected_term': selected_term,
        'all_terms': all_terms,
        'total_subjects': total_subjects,
        'overall_average': overall_average,
        'class_position': class_position,
        'comment': comment,
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

    total_subjects = results.count()
    overall_average = (
        round(sum(r.total_score for r in results) / total_subjects, 1)
        if total_subjects else 0
    )
    class_position = None
    if student.class_arm and selected_term:
        class_position = calculate_class_position(student.class_arm, selected_term).get(student.id)
    comment = generate_comment(overall_average) if total_subjects else None

    return render(request, 'school/view_student_results_as_teacher.html', {
        'student': student,
        'results': results,
        'selected_term': selected_term,
        'all_terms': all_terms,
        'total_subjects': total_subjects,
        'overall_average': overall_average,
        'class_position': class_position,
        'comment': comment,
    })
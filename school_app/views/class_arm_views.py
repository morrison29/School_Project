from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from school_app.models import ClassArm, StudentProfile, TeacherProfile
from school_app.decorators import admin_required, teacher_required, student_required, admin_or_teacher_required

@admin_required
def create_class_arm(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()

        if not name:
            messages.error(request, "Class arm name is required.")
            return redirect('school_app:create_class_arm')

        if ClassArm.objects.filter(name__iexact=name).exists():
            messages.error(request, "Class arm with this name already exists.")
            return redirect('school_app:create_class_arm')

        ClassArm.objects.create(name=name)
        messages.success(request, "Class arm created successfully.")
        return redirect('school_app:view_all_class_arms')

    return render(request, 'school/create_class_arm.html')


@admin_required
def view_all_class_arms(request):
    class_arms = ClassArm.objects.all()
    return render(request, 'school/view_all_class_arms.html', {'class_arms': class_arms})


@admin_or_teacher_required
def view_classarm(request, class_arm_id):
    class_arm = get_object_or_404(ClassArm, id=class_arm_id)
    students = StudentProfile.objects.filter(class_arm=class_arm)
    teacher = TeacherProfile.objects.filter(class_arm=class_arm).first()
    subjects = class_arm.subjects.all()
    return render(request, 'school/view_classarm.html', {
        'class_arms': class_arm,
        'students': students,
        'teacher': teacher,
        'subjects': subjects,
    })


@admin_or_teacher_required
def view_students_in_class_arm(request, class_arm_id):
    class_arm = get_object_or_404(ClassArm, id=class_arm_id)
    students = StudentProfile.objects.filter(class_arm=class_arm)
    return render(request, 'school/view_students_in_class_arm.html', {'class_arm': class_arm, 'students': students})


@admin_required
@require_POST
def delete_class_arm(request, class_arm_id):
    class_arm = get_object_or_404(ClassArm, id=class_arm_id)
    class_arm.delete()
    messages.success(request, "Class arm deleted successfully.")
    return redirect('school_app:view_all_class_arms')


@admin_required
@require_POST
def promote_students(request, class_arm_id):
    class_arm = get_object_or_404(ClassArm, id=class_arm_id)
    StudentProfile.objects.filter(class_arm=class_arm).update(class_arm=None)
    messages.success(request, "Students promoted successfully.")
    return redirect('school_app:view_classarm', class_arm_id=class_arm_id)


# ---------------------------------------------------------------------------
# Teacher <-> class arm assignment
# ---------------------------------------------------------------------------

@admin_required
def assign_teacher_class_arm(request):
    if request.method == 'POST':
        teacher_id = request.POST.get('teacher_id')
        class_arm_id = request.POST.get('class_arm')

        try:
            teacher = TeacherProfile.objects.get(id=teacher_id)
            class_arm = ClassArm.objects.get(id=class_arm_id)
        except TeacherProfile.DoesNotExist:
            messages.error(request, "Teacher not found.")
            return redirect('school_app:assign_teacher_class')
        except ClassArm.DoesNotExist:
            messages.error(request, "Class arm not found.")
            return redirect('school_app:assign_teacher_class')

        if teacher.class_arm is not None:
            messages.error(request, "Teacher is already assigned to a class arm.")
            return redirect('school_app:assign_teacher_class')

        if TeacherProfile.objects.filter(class_arm=class_arm).exists():
            messages.error(request, "Class arm already has a teacher assigned.")
            return redirect('school_app:assign_teacher_class')

        teacher.class_arm = class_arm
        teacher.save()
        messages.success(request, "Teacher assigned to class successfully.")
        return redirect('school_app:view_all_class_arms')

    return render(request, 'school/assign_teacher_class_arm.html', {
        'teachers': TeacherProfile.objects.all(),
        'class_arms': ClassArm.objects.all(),
    })


@admin_required
def update_teacher_class_arm(request, teacher_id):
    teacher = get_object_or_404(TeacherProfile, id=teacher_id)

    if request.method == 'POST':
        class_arm_id = request.POST.get('class_arm')

        try:
            class_arm = ClassArm.objects.get(id=class_arm_id)
        except ClassArm.DoesNotExist:
            messages.error(request, "Class arm not found.")
            return redirect('school_app:update_teacher_class_arm', teacher_id=teacher_id)

        if TeacherProfile.objects.filter(class_arm=class_arm).exclude(id=teacher_id).exists():
            messages.error(request, "Class arm already has a teacher assigned.")
            return redirect('school_app:update_teacher_class_arm', teacher_id=teacher_id)

        teacher.class_arm = class_arm
        teacher.save()
        messages.success(request, "Teacher's class arm updated successfully.")
        return redirect('school_app:admin-dashboard')

    return render(request, 'school/update_teacher_class_arm.html', {'teacher': teacher, 'class_arms': ClassArm.objects.all()})


@admin_required
@require_POST
def remove_teacher_class_arm(request, teacher_id):
    teacher = get_object_or_404(TeacherProfile, id=teacher_id)
    teacher.class_arm = None
    teacher.save()
    messages.success(request, "Teacher's class arm removed successfully.")
    return redirect('school_app:admin-dashboard')


# ---------------------------------------------------------------------------
# Student <-> class arm assignment
# ---------------------------------------------------------------------------

@admin_required
def assign_student_class_arm(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        class_arm_id = request.POST.get('class_arm')

        try:
            student_profile = StudentProfile.objects.get(id=student_id)
            class_arm = ClassArm.objects.get(id=class_arm_id)
        except StudentProfile.DoesNotExist:
            messages.error(request, "Student not found.")
            return redirect('school_app:assign_student_class')
        except ClassArm.DoesNotExist:
            messages.error(request, "Class arm not found.")
            return redirect('school_app:assign_student_class')

        if student_profile.class_arm is not None:
            messages.error(request, "Student is already assigned to a class arm.")
            return redirect('school_app:assign_student_class')

        student_profile.class_arm = class_arm
        student_profile.save()
        messages.success(request, "Student assigned to class successfully.")
        return redirect('school_app:view_all_class_arms')

    return render(request, 'school/assign_student_class_arm.html', {
        'students': StudentProfile.objects.all(),
        'class_arms': ClassArm.objects.all(),
    })


@admin_required
@require_POST
def remove_student_class_arm(request, student_id):
    student = get_object_or_404(StudentProfile, id=student_id)
    student.class_arm = None
    student.save()
    messages.success(request, "Student's class arm removed successfully.")
    return redirect('school_app:admin-dashboard')

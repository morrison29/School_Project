import random
from django.db.models import Sum
from .models import Result
from school_app.models import Term, AcademicSession

def get_current_term():
    return Term.objects.filter(is_current=True).select_related('session').first()

def get_current_session():
    return AcademicSession.objects.filter(is_current=True).first()

def generate_otp():
    return random.randint(100000, 999999)

def calculate_total_score(test_score, assignment_score, exam_score):
    return test_score + assignment_score + exam_score

def calculate_grade(total_score):
    if total_score >= 85:
        return 'A'
    elif total_score >= 75:
        return 'B'
    elif total_score >= 65:
        return 'C'
    elif total_score >= 55:
        return 'D'
    elif total_score >= 50:
        return 'E'
    else:
        return 'F'
    
def compute_positions(class_arm, subject):
    students_results = Result.objects.filter(class_arm=class_arm, subject=subject).annotate(grand_total=Sum('total_score')).order_by('-grand_total')
    position = 1

    for entry in students_results:
        student_id = entry.student.id
        
    Result.objects.filter(student_id=student_id, subject=subject, class_arm=class_arm).update(position=position)
    position += 1

def generate_comment(average):
    if average >= 90:
        return "Outstanding performance. Keep up the excellent work!"
    elif average >= 80:
        return "Very good result. Consistent effort is showing."
    elif average >= 70:
        return "Good performance. There's room to push a little further."
    elif average >= 60:
        return "Fair result. More consistent effort is needed."
    elif average >= 50:
        return "Below average. Needs to put in more work."
    else:
        return "Poor performance. Requires serious improvement and support."
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
# Create your models here.

class AdminProfile(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=11)
    address = models.TextField()

    def __str__(self):
        return f"{self.user.username} - Admin"

class EmailOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    attempts =  models.IntegerField(default=0)

    def is_expired(self):
        expiration_time = self.created_at + timezone.timedelta(minutes=60)
        return timezone.now() > expiration_time
    
    def __str__(self):
        return f"{self.email} - {self.otp} - Verified: {self.is_verified}"

class AcademicSession(models.Model):
    name = models.CharField(max_length=20, unique=True)  # e.g. "2025/2026"
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['-name']

    def __str__(self):
        return self.name


class Term(models.Model):
    FIRST = 'first'
    SECOND = 'second'
    THIRD = 'third'
    TERM_CHOICES = [
        (FIRST, 'First Term'),
        (SECOND, 'Second Term'),
        (THIRD, 'Third Term'),
    ]
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='terms')
    name = models.CharField(max_length=10, choices=TERM_CHOICES)
    is_current = models.BooleanField(default=False)

    class Meta:
        unique_together = ('session', 'name')
        ordering = ['session__name', 'name']

    def __str__(self):
        return f"{self.get_name_display()} - {self.session.name}"
    
class ClassArm(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    subjects = models.ManyToManyField('Subject', blank=True)

    def __str__(self):
        return self.name

class TeacherProfile(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    phone_number = models.CharField(max_length=11)
    address = models.TextField()
    class_arm = models.ForeignKey(ClassArm, blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.user.username} - Teacher "
    

class StudentProfile(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    registration_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    phone_number = models.CharField(max_length=11)
    class_arm = models.ForeignKey(ClassArm, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.registration_number}"

class Subject(models.Model):
    id = models.AutoField(primary_key=True)
    subject_name = models.CharField(max_length=100)

    def __str__(self):
        return self.subject_name
    
class MidtermAssignment(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_arm = models.ForeignKey(ClassArm, on_delete=models.CASCADE)
    due_date = models.DateField()
   

    def __str__(self):
        return f"{self.title} - {self.subject.subject_name}"

class MidtermSubmission(models.Model):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    assignment = models.ForeignKey(MidtermAssignment, on_delete=models.CASCADE)
    answer = models.TextField()
    answer2 = models.FileField(upload_to='assignments/', null=True, blank=True) 
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'assignment')
    def __str__(self):
        return f"{self.student.user.username} - {self.assignment.title}"

class Result(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_arm = models.ForeignKey(ClassArm, on_delete=models.CASCADE, null=True, blank=True)

    test_score = models.FloatField(null=True, blank=True)
    assignment_score = models.FloatField(null=True, blank=True)
    exam_score = models.FloatField(null=True, blank=True)
    total_score = models.FloatField(editable=False)
    grade = models.CharField(max_length=2, editable=False, null=True, blank=True)
    average = models.FloatField(null=True, blank=True)
    position = models.PositiveIntegerField(null=True, blank=True)
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='results', null=True, blank=True)
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='results', null=True, blank=True)

    class Meta:
        unique_together = ('student', 'subject', 'class_arm', 'term')

    def __str__(self):
        return f"{self.student.user.username} - {self.subject.subject_name}"


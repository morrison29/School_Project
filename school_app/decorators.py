TEACHERS_GROUP = 'Teachers'
STUDENT_GROUP = 'Students'
from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(check_func, error_message, redirect_view='school_app:login'):
    """Decorator factory: requires login AND a custom role check."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not check_func(request.user):
                messages.error(request, error_message)
                return redirect(redirect_view)
            return view_func(request, *args, **kwargs)
        return login_required(_wrapped)
    return decorator


def admin_required(view_func):
    return role_required(
        lambda u: u.is_superuser,
        "Only admin allowed.",
    )(view_func)


def teacher_required(view_func):
    return role_required(
        lambda u: u.groups.filter(name=TEACHERS_GROUP).exists(),
        "Only teachers allowed.",
    )(view_func)


def student_required(view_func):
    return role_required(
        lambda u: u.groups.filter(name=STUDENT_GROUP).exists(),
        "Only students allowed.",
    )(view_func)


def admin_or_teacher_required(view_func):
    return role_required(
        lambda u: u.is_superuser or u.groups.filter(name=TEACHERS_GROUP).exists(),
        "Only admin or teacher allowed.",
    )(view_func)

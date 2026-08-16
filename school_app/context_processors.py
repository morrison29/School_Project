from school_app.models import Term

def current_term_context(request):
    return {
        'global_current_term': Term.objects.filter(is_current=True).select_related('session').first()
    }
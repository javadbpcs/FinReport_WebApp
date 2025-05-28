from .models import Report

def reports_processor(request):
    """
    Context processor to include reports in all templates
    """
    return {'reports': Report.objects.all().order_by('-created_at')} 
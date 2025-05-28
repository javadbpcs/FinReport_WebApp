from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from .models import Report
from stock_analyzer.models import StockAnalysis
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from _stock_info_.polygon_stock_info import get_stock_info
from django.views.decorators.http import require_POST

# Create your views here.

def get_reports_context():
    return {'reports': Report.objects.all().order_by('-created_at')}

def report1(request):
    context = get_reports_context()
    return render(request, 'dashboard/report1.html', context)

def report2(request):
    context = get_reports_context()
    return render(request, 'dashboard/report2.html', context)

def new_report(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        report_type = request.POST.get('report_type')
        description = request.POST.get('description')
        if name and report_type:
            report = Report.objects.create(
                name=name,
                report_type=report_type,
                description=description
            )
            return redirect('dashboard:view_report', report_id=report.id)
    
    context = {
        'report_styles': Report.REPORT_TYPES,
        **get_reports_context()
    }
    return render(request, 'dashboard/new_report.html', context)

def view_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    latest_analysis = StockAnalysis.objects.filter(report=report).order_by('-created_at').first()
    
    context = {
        'report': report,
        'latest_analysis': latest_analysis,
        **get_reports_context()
    }
    
    return render(request, 'dashboard/view_report.html', context)

def delete_report(request, report_id):
    if request.method == 'POST':
        report = get_object_or_404(Report, id=report_id)
        report.delete()
        return redirect('dashboard:new_report')
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def rename_report(request, report_id):
    if request.method == 'POST':
        report = get_object_or_404(Report, id=report_id)
        new_name = request.POST.get('name')
        if new_name:
            report.name = new_name
            report.save()
            return JsonResponse({'success': True, 'new_name': new_name})
    return JsonResponse({'error': 'Invalid request'}, status=400)

def submit_text(request, report_id):
    if request.method == 'POST':
        report = get_object_or_404(Report, id=report_id)
        submitted_text = request.POST.get('submitted_text')
        
        if submitted_text:
            report.submitted_text = submitted_text
            report.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Text cannot be empty'}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

@require_POST
def get_stock_info_view(request, report_id):
    """
    View to handle stock information requests
    """
    try:
        stock_symbol = request.POST.get('stock_symbol', '').upper()
        if not stock_symbol:
            return JsonResponse({'error': 'Stock symbol is required'}, status=400)
        
        # Get stock information using Polygon.io
        stock_info = get_stock_info(stock_symbol)
        
        if 'error' in stock_info:
            return JsonResponse({'error': stock_info['error']}, status=400)
        
        return JsonResponse({
            'success': True,
            'data': stock_info
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

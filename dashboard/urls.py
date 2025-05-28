from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('report1/', views.report1, name='report1'),
    path('report2/', views.report2, name='report2'),
    path('new-report/', views.new_report, name='new_report'),
    path('report/<int:report_id>/', views.view_report, name='view_report'),
    path('report/<int:report_id>/delete/', views.delete_report, name='delete_report'),
    path('report/<int:report_id>/rename/', views.rename_report, name='rename_report'),
    path('report/<int:report_id>/submit-text/', views.submit_text, name='submit_text'),
    path('report/<int:report_id>/stock-info/', views.get_stock_info_view, name='get_stock_info'),
] 
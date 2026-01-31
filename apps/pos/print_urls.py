"""URL configuration for Print Agent API"""
from django.urls import path
from apps.pos import print_api

urlpatterns = [
    path('register/', print_api.register_terminal, name='register_terminal'),
    path('jobs/', print_api.get_print_jobs, name='get_print_jobs'),
    path('jobs/<int:job_id>/complete/', print_api.mark_job_completed, name='mark_job_completed'),
    path('jobs/<int:job_id>/failed/', print_api.mark_job_failed, name='mark_job_failed'),
    path('jobs/<int:job_id>/status/', print_api.update_job_status, name='update_job_status'),
    path('heartbeat/', print_api.heartbeat, name='heartbeat'),
]

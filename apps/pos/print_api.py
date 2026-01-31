"""
Print API for Print Agent Communication
RESTful API endpoints for print job queue
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import models
from django.conf import settings
import json


# Simple API key authentication
def verify_api_key(request, api_key=None):
    """Verify API key from request"""
    # Skip authentication if not required (development mode)
    if not getattr(settings, 'PRINT_AGENT_AUTH_REQUIRED', False):
        return True
    
    if api_key is None:
        # Try to get from POST/GET
        api_key = request.POST.get('api_key') or request.GET.get('api_key')
        
        # Try to get from JSON body
        if not api_key and request.body:
            try:
                data = json.loads(request.body)
                api_key = data.get('api_key')
            except (json.JSONDecodeError, AttributeError):
                pass
    
    # Verify against configured API key
    expected_key = getattr(settings, 'PRINT_AGENT_API_KEY', 'your-secret-api-key-here')
    return api_key == expected_key


@csrf_exempt
@require_http_methods(['POST'])
def register_terminal(request):
    """Register a print agent terminal"""
    try:
        data = json.loads(request.body)
        terminal_id = data.get('terminal_id')
        api_key = data.get('api_key')
        
        if not verify_api_key(request, api_key):
            return JsonResponse({'error': 'Invalid API key'}, status=401)
        
        # TODO: Save terminal info to database
        # For now, just acknowledge
        return JsonResponse({
            'success': True,
            'terminal_id': terminal_id,
            'message': 'Terminal registered successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(['GET'])
def get_print_jobs(request):
    """Get pending print jobs for a terminal"""
    if not verify_api_key(request):
        return JsonResponse({'error': 'Invalid API key'}, status=401)
    
    terminal_id = request.GET.get('terminal_id')
    status = request.GET.get('status', 'pending')
    print(f"\n[PRINT API] GET /api/print/jobs/ - terminal_id={terminal_id}, status={status}")
    
    # Import here to avoid circular import
    from apps.pos.models import PrintJob
    
    # Get jobs for this terminal
    jobs = PrintJob.objects.filter(
        terminal_id=terminal_id,
        status=status
    ).order_by('created_at')[:10]  # Max 10 jobs per poll
    
    print(f"[PRINT API] Found {jobs.count()} {status} jobs for {terminal_id}")
    
    job_list = []
    for job in jobs:
        print(f"[PRINT API]   - Job #{job.id} (UUID: {job.job_uuid}): {job.job_type}")
        job_list.append({
            'id': job.id,
            'job_uuid': str(job.job_uuid),
            'job_type': job.job_type,
            'receipt_data': job.content,  # Structured receipt data
            'created_at': job.created_at.isoformat(),
            'retry_count': job.retry_count,
        })
    
    return JsonResponse(job_list, safe=False)


@csrf_exempt
@require_http_methods(['POST'])
def mark_job_completed(request, job_id):
    """Mark a print job as completed"""
    if not verify_api_key(request):
        return JsonResponse({'error': 'Invalid API key'}, status=401)
    
    from apps.pos.models import PrintJob
    
    try:
        job = PrintJob.objects.get(id=job_id)
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.save()
        
        return JsonResponse({
            'success': True,
            'job_id': job_id
        })
        
    except PrintJob.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)


@csrf_exempt
@require_http_methods(['POST'])
def mark_job_failed(request, job_id):
    """Mark a print job as failed"""
    if not verify_api_key(request):
        return JsonResponse({'error': 'Invalid API key'}, status=401)
    
    from apps.pos.models import PrintJob
    
    try:
        data = json.loads(request.body)
        error_code = data.get('error_code', 'UNKNOWN_ERROR')
        error_message = data.get('error_message', data.get('error', 'Unknown error'))
        
        job = PrintJob.objects.get(id=job_id)
        job.status = 'failed'
        job.error_code = error_code
        job.error_message = error_message
        job.retry_count += 1
        job.completed_at = timezone.now()
        job.save()
        
        return JsonResponse({
            'success': True,
            'job_id': job_id
        })
        
    except PrintJob.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)


@csrf_exempt
@require_http_methods(['POST'])
def update_job_status(request, job_id):
    """
    Update job status (fetched, printing, etc.)
    Enables lifecycle tracking
    """
    if not verify_api_key(request):
        return JsonResponse({'error': 'Invalid API key'}, status=401)
    
    from apps.pos.models import PrintJob
    
    try:
        data = json.loads(request.body)
        status = data.get('status')
        
        job = PrintJob.objects.get(id=job_id)
        job.status = status
        
        # Track when job was fetched
        if status == 'fetched' and not job.fetched_at:
            job.fetched_at = timezone.now()
        
        job.save()
        
        return JsonResponse({
            'success': True,
            'job_id': job_id,
            'status': status
        })
        
    except PrintJob.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)


@csrf_exempt
@require_http_methods(['POST'])
def heartbeat(request):
    """
    Receive heartbeat from Print Agent
    Tracks agent health and printer status
    """
    if not verify_api_key(request):
        return JsonResponse({'error': 'Invalid API key'}, status=401)
    
    try:
        data = json.loads(request.body)
        terminal_id = data.get('terminal_id')
        printer_status = data.get('printer_status')
        agent_status = data.get('agent_status')
        
        # TODO: Save heartbeat to database for monitoring
        # For now, just log it
        print(f"[HEARTBEAT] {terminal_id} - Printer: {printer_status}, Agent: {agent_status}")
        
        return JsonResponse({
            'success': True,
            'server_time': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

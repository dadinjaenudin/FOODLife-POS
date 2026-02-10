"""
Customer Display API
API endpoints untuk customer display slideshow
- Get slideshow config (brand/store specific)
- Upload images to MinIO
- Manage slides
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.files.storage import default_storage
from django.db import models
import json
import uuid
from datetime import date
from functools import wraps

from .models import CustomerDisplaySlide, Brand, Store, Company
from .minio_client import upload_to_minio, delete_from_minio, get_minio_url


def cors_allow_all(view_func):
    """
    Decorator to add CORS headers to response
    Allows requests from any origin (for customer display access)
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            response = JsonResponse({'status': 'ok'})
        else:
            response = view_func(request, *args, **kwargs)
        
        # Add CORS headers
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response['Access-Control-Max-Age'] = '86400'  # 24 hours
        
        return response
    return wrapper


@csrf_exempt
@cors_allow_all
@require_http_methods(['GET', 'OPTIONS'])
def get_slideshow_config(request):
    """
    Get slideshow configuration for customer display
    Filter by company, brand, store from query params
    
    GET /api/customer-display/slideshow?company=YOGYA&brand=BOE&store=KPT
    
    Response:
    {
        "success": true,
        "slides": [
            {
                "id": 123,
                "title": "Promo Spesial",
                "image_url": "http://minio:9000/customer-display/slide1.jpg",
                "duration": 5,
                "order": 1
            }
        ],
        "running_text": "Selamat datang...",
        "brand_name": "YOGYA Food Life",
        "brand_logo": "http://minio:9000/brands/boe-logo.png"
    }
    """
    try:
        # Get filter params
        company_code = request.GET.get('company')
        brand_code = request.GET.get('brand')
        store_code = request.GET.get('store')
        
        # Base query - active slides only
        query = CustomerDisplaySlide.objects.filter(
            is_active=True
        ).select_related('company', 'brand', 'store')
        
        # Filter by date (start_date/end_date)
        today = date.today()
        query = query.filter(
            models.Q(start_date__isnull=True) | models.Q(start_date__lte=today)
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=today)
        )
        
        # Get Company
        company = None
        if company_code:
            try:
                company = Company.objects.get(code=company_code)
                query = query.filter(company=company)
            except Company.DoesNotExist:
                pass
        
        # Get Brand
        brand = None
        brand_name = None
        brand_logo = None
        if brand_code:
            try:
                brand = Brand.objects.select_related('company').get(code=brand_code)
                brand_name = brand.name
                # Get brand logo URL if available
                if brand.logo:
                    # Build full URL for logo
                    request_scheme = request.scheme
                    request_host = request.get_host()
                    brand_logo = f"{request_scheme}://{request_host}{brand.logo.url}"
                # Filter: brand-specific OR company-wide (no brand/store)
                query = query.filter(
                    models.Q(brand=brand) | 
                    models.Q(brand__isnull=True, store__isnull=True)
                )
            except Brand.DoesNotExist:
                pass
        
        # Get Store
        store = None
        if store_code:
            try:
                store = Store.objects.select_related('company').get(store_code=store_code)
                # Filter: store-specific OR brand-specific OR company-wide
                query = query.filter(
                    models.Q(store=store) |
                    models.Q(brand=brand, store__isnull=True) if brand else models.Q(store=store) |
                    models.Q(brand__isnull=True, store__isnull=True)
                )
            except Store.DoesNotExist:
                pass
        
        # Get slides ordered
        slides = query.order_by('order', '-created_at')
        
        # Build response
        slides_data = []
        for slide in slides:
            slides_data.append({
                'id': slide.id,
                'title': slide.title,
                'image_url': slide.image_url,
                'duration': slide.duration_seconds,
                'order': slide.order
            })
        
        # Get running text from store/brand config if available
        running_text = "🎉 Selamat datang di YOGYA Food Life! • Nikmati berbagai menu pilihan terbaik • Terima kasih atas kunjungan Anda"
        if store and hasattr(store, 'running_text'):
            running_text = store.running_text
        elif brand and hasattr(brand, 'running_text'):
            running_text = brand.running_text
        
        return JsonResponse({
            'success': True,
            'slides': slides_data,
            'running_text': running_text,
            'brand_name': brand_name,
            'brand_logo': brand_logo,
            'total_slides': len(slides_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def upload_slide(request):
    """
    Upload new slide to MinIO and create database record
    
    POST /api/customer-display/upload
    Content-Type: multipart/form-data
    
    Form fields:
    - image: image file (required)
    - title: slide title (required)
    - description: description (optional)
    - company_code: company code (required)
    - brand_code: brand code (optional)
    - store_code: store code (optional)
    - order: display order (optional, default=0)
    - duration: duration in seconds (optional, default=5)
    
    Response:
    {
        "success": true,
        "slide": {
            "id": 123,
            "title": "New Promo",
            "image_url": "http://minio:9000/customer-display/slide.jpg",
            "order": 1
        }
    }
    """
    try:
        # Check authentication
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        # Get form data
        image_file = request.FILES.get('image')
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        company_code = request.POST.get('company_code')
        brand_code = request.POST.get('brand_code')
        store_code = request.POST.get('store_code')
        order = int(request.POST.get('order', 0))
        duration = int(request.POST.get('duration', 5))
        
        # Validate required fields
        if not image_file:
            return JsonResponse({
                'success': False,
                'error': 'Image file is required'
            }, status=400)
        
        if not title:
            return JsonResponse({
                'success': False,
                'error': 'Title is required'
            }, status=400)
        
        if not company_code:
            return JsonResponse({
                'success': False,
                'error': 'Company code is required'
            }, status=400)
        
        # Validate company
        try:
            company = Company.objects.get(code=company_code)
        except Company.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Company {company_code} not found'
            }, status=404)
        
        # Validate brand (optional)
        brand = None
        if brand_code:
            try:
                brand = Brand.objects.get(code=brand_code, company=company)
            except Brand.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Brand {brand_code} not found'
                }, status=404)
        
        # Validate store (optional)
        store = None
        if store_code:
            try:
                store = Store.objects.get(code=store_code)
                if brand and store.brand != brand:
                    return JsonResponse({
                        'success': False,
                        'error': f'Store {store_code} does not belong to brand {brand_code}'
                    }, status=400)
            except Store.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Store {store_code} not found'
                }, status=404)
        
        # Generate unique filename
        file_ext = image_file.name.split('.')[-1]
        unique_id = str(uuid.uuid4())[:8]
        filename = f"slide_{unique_id}.{file_ext}"
        
        # Upload to MinIO
        bucket_name = 'customer-display'
        object_path = f"{company_code}/{brand_code or 'all'}/{filename}"
        
        try:
            # Upload to MinIO (you need to implement this function)
            image_url = upload_to_minio(
                bucket_name=bucket_name,
                object_name=object_path,
                file_data=image_file.read(),
                content_type=image_file.content_type
            )
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Failed to upload to MinIO: {str(e)}'
            }, status=500)
        
        # Create database record
        slide = CustomerDisplaySlide.objects.create(
            company=company,
            brand=brand,
            store=store,
            title=title,
            description=description,
            image_url=image_url,
            image_path=object_path,
            order=order,
            duration_seconds=duration,
            is_active=True,
            created_by=request.user,
            updated_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'slide': {
                'id': slide.id,
                'title': slide.title,
                'image_url': slide.image_url,
                'duration': slide.duration_seconds,
                'order': slide.order,
                'created_at': slide.created_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(['DELETE'])
def delete_slide(request, slide_id):
    """
    Delete slide from database and MinIO
    
    DELETE /api/customer-display/slide/<id>
    
    Response:
    {
        "success": true,
        "message": "Slide deleted successfully"
    }
    """
    try:
        # Check authentication
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        # Get slide
        try:
            slide = CustomerDisplaySlide.objects.get(id=slide_id)
        except CustomerDisplaySlide.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Slide not found'
            }, status=404)
        
        # Delete from MinIO
        try:
            delete_from_minio(slide.image_path)
        except Exception as e:
            # Log but don't fail if MinIO delete fails
            print(f"Warning: Failed to delete from MinIO: {e}")
        
        # Delete from database
        slide.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Slide deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(['PATCH'])
def update_slide(request, slide_id):
    """
    Update slide metadata (not image)
    
    PATCH /api/customer-display/slide/<id>
    Body: {
        "title": "Updated Title",
        "order": 5,
        "duration": 10,
        "is_active": false
    }
    
    Response:
    {
        "success": true,
        "slide": {...}
    }
    """
    try:
        # Check authentication
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        # Get slide
        try:
            slide = CustomerDisplaySlide.objects.get(id=slide_id)
        except CustomerDisplaySlide.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Slide not found'
            }, status=404)
        
        # Parse request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON'
            }, status=400)
        
        # Update fields
        if 'title' in data:
            slide.title = data['title']
        if 'description' in data:
            slide.description = data['description']
        if 'order' in data:
            slide.order = int(data['order'])
        if 'duration' in data:
            slide.duration_seconds = int(data['duration'])
        if 'is_active' in data:
            slide.is_active = bool(data['is_active'])
        if 'start_date' in data:
            slide.start_date = data['start_date']
        if 'end_date' in data:
            slide.end_date = data['end_date']
        
        slide.updated_by = request.user
        slide.save()
        
        return JsonResponse({
            'success': True,
            'slide': {
                'id': slide.id,
                'title': slide.title,
                'image_url': slide.image_url,
                'duration': slide.duration_seconds,
                'order': slide.order,
                'is_active': slide.is_active,
                'updated_at': slide.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@cors_allow_all
@require_http_methods(['GET', 'OPTIONS'])
def get_display_config(request):
    """
    Get customer display configuration (branding, theme, running text)
    Filter by company, brand, store from query params
    
    GET /api/customer-display/config?company=YOGYA&brand=BOE&store=KPT
    
    Response:
    {
        "success": true,
        "config": {
            "brand_name": "YOGYA Food Life",
            "brand_logo_url": "http://minio:9000/brands/logo.png",
            "brand_tagline": "Nikmati berbagai menu pilihan",
            "running_text": "Selamat datang di YOGYA Food Life...",
            "running_text_speed": 50,
            "theme": {
                "primary_color": "#4F46E5",
                "secondary_color": "#10B981",
                "text_color": "#1F2937",
                "billing_bg": "gradient",
                "billing_text": "#FFFFFF"
            }
        }
    }
    """
    try:
        from .models import CustomerDisplayConfig
        
        # Get filter params
        company_code = request.GET.get('company')
        brand_code = request.GET.get('brand')
        store_code = request.GET.get('store')
        
        # Resolve company, brand, store
        company = None
        brand = None
        store = None
        
        if company_code:
            try:
                company = Company.objects.get(code=company_code)
            except Company.DoesNotExist:
                pass
        
        if brand_code:
            try:
                brand = Brand.objects.get(code=brand_code)
            except Brand.DoesNotExist:
                pass
        
        if store_code:
            try:
                store = Store.objects.get(store_code=store_code)
            except Store.DoesNotExist:
                pass
        
        # Find most specific config (store > brand > company)
        config = None
        
        # Try store-specific config first
        if store and company:
            config = CustomerDisplayConfig.objects.filter(
                company=company,
                store=store,
                is_active=True
            ).first()
        
        # Try brand-specific config
        if not config and brand and company:
            config = CustomerDisplayConfig.objects.filter(
                company=company,
                brand=brand,
                store__isnull=True,
                is_active=True
            ).first()
        
        # Try company-wide config
        if not config and company:
            config = CustomerDisplayConfig.objects.filter(
                company=company,
                brand__isnull=True,
                store__isnull=True,
                is_active=True
            ).first()
        
        # If no config found, return default
        if not config:
            return JsonResponse({
                'success': True,
                'config': {
                    'brand_name': 'POS System',
                    'brand_logo_url': None,
                    'brand_tagline': '',
                    'running_text': '🎉 Selamat datang! • Welcome! • Terima kasih atas kunjungan Anda',
                    'running_text_speed': 50,
                    'theme': {
                        'primary_color': '#4F46E5',
                        'secondary_color': '#10B981',
                        'text_color': '#1F2937',
                        'billing_bg': 'gradient',
                        'billing_text': '#FFFFFF'
                    }
                }
            })
        
        # Build response
        return JsonResponse({
            'success': True,
            'config': {
                'brand_name': config.brand_name,
                'brand_logo_url': config.get_logo_url(request),
                'brand_tagline': config.brand_tagline,
                'running_text': config.running_text,
                'running_text_speed': config.running_text_speed,
                'theme': {
                    'primary_color': config.theme_primary_color,
                    'secondary_color': config.theme_secondary_color,
                    'text_color': config.theme_text_color,
                    'billing_bg': config.theme_billing_bg,
                    'billing_text': config.theme_billing_text
                }
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

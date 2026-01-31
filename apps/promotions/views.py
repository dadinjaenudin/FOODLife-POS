from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
from decimal import Decimal

from .models import Promotion, PromotionUsage
from apps.pos.models import Bill
from apps.core.models import Product, Store
from .engine import PromotionEngine, Cart, CartItem


def trigger_client_event(response, event_name, data=None):
    if data:
        response['HX-Trigger'] = json.dumps({event_name: data})
    else:
        response['HX-Trigger'] = event_name
    return response


@login_required
@require_http_methods(["POST"])
def apply_promotion(request, bill_id):
    """Apply promotion to bill - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id, status='open')
    promo_id = request.POST.get('promo_id')
    
    promo = get_object_or_404(Promotion, id=promo_id)
    
    if not promo.is_valid_now():
        return HttpResponse('<div class="p-3 bg-red-100 text-red-700 rounded">Promo tidak berlaku</div>')
    
    if BillPromotion.objects.filter(bill=bill, promotion=promo).exists():
        return HttpResponse('<div class="p-3 bg-yellow-100 text-yellow-700 rounded">Promo sudah digunakan</div>')
    
    discount = promo.calculate_discount(bill)
    
    if discount <= 0:
        return HttpResponse(
            '<div class="p-3 bg-yellow-100 text-yellow-700 rounded">Promo tidak berlaku untuk pesanan ini</div>'
        )
    
    BillPromotion.objects.create(
        bill=bill,
        promotion=promo,
        discount_amount=discount,
        applied_by=request.user,
    )
    
    promo.current_uses += 1
    promo.save()
    
    bill.discount_amount += discount
    bill.calculate_totals()
    
    response = render(request, 'pos/partials/bill_panel.html', {'bill': bill})
    return trigger_client_event(response, 'promoApplied')


@login_required
@require_http_methods(["POST"])
def remove_promotion(request, bill_promo_id):
    """Remove applied promotion from bill - HTMX"""
    bill_promo = get_object_or_404(BillPromotion, id=bill_promo_id)
    bill = bill_promo.bill
    
    if bill.status != 'open':
        return HttpResponse('<div class="p-3 bg-red-100 text-red-700 rounded">Bill sudah ditutup</div>')
    
    if bill_promo.voucher:
        bill_promo.voucher.status = 'active'
        bill_promo.voucher.used_at = None
        bill_promo.voucher.used_by = None
        bill_promo.voucher.used_bill = None
        bill_promo.voucher.save()
    
    bill_promo.promotion.current_uses -= 1
    bill_promo.promotion.save()
    
    bill.discount_amount -= bill_promo.discount_amount
    bill_promo.delete()
    bill.calculate_totals()
    
    return render(request, 'pos/partials/bill_panel.html', {'bill': bill})


# ============================================
# PROMOTION TESTING UI
# ============================================

@login_required
def promotion_test_page(request):
    """Promotion Testing UI - Test promotion engine"""
    store_config = Store.get_current()
    brand = store_config.brand
    
    # Get all products for search
    products = Product.objects.filter(
        category__brand=brand,
        is_active=True
    ).select_related('category').order_by('name')[:50]
    
    # Get active promotions
    promotions = Promotion.objects.filter(
        brand=brand,
        is_active=True
    ).order_by('execution_priority')
    
    # Get cart from session
    cart_data = request.session.get('test_cart', [])
    
    context = {
        'products': products,
        'promotions': promotions,
        'cart_items': cart_data,
    }
    
    return render(request, 'promotions/test_engine.html', context)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def test_add_to_cart(request):
    """Add product to test cart (session-based)"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        product = get_object_or_404(Product, id=product_id)
        
        # Get cart from session
        cart_data = request.session.get('test_cart', [])
        
        # Check if product already in cart
        found = False
        for item in cart_data:
            if item['product_id'] == str(product_id):
                item['quantity'] += quantity
                found = True
                break
        
        if not found:
            cart_data.append({
                'product_id': str(product.id),
                'product_name': product.name,
                'sku': product.sku,
                'price': float(product.price),
                'quantity': quantity,
                'category_id': str(product.category.id) if product.category else None,
            })
        
        request.session['test_cart'] = cart_data
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'cart': cart_data,
            'cart_count': len(cart_data)
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def test_calculate_promotions(request):
    """Calculate promotions for test cart"""
    try:
        store_config = Store.get_current()
        brand = store_config.brand
        
        # Get cart from session
        cart_data = request.session.get('test_cart', [])
        
        if not cart_data:
            return JsonResponse({
                'success': False,
                'error': 'Cart is empty'
            }, status=400)
        
        # Build cart items
        cart_items = []
        for item_data in cart_data:
            cart_item = CartItem(
                product_id=item_data['product_id'],
                product_name=item_data['product_name'],
                sku=item_data['sku'],
                price=item_data['price'],
                quantity=item_data['quantity'],
                category_id=item_data.get('category_id')
            )
            cart_items.append(cart_item)
        
        # Create cart
        cart = Cart(cart_items, brand, store_config)
        
        # Initialize engine
        engine = PromotionEngine(brand, store_config)
        
        # Apply promotions
        result = engine.apply_promotions_to_cart(cart, auto_apply_only=False)
        
        # Format results
        applied_promotions = []
        for promo_result in result['applied_promotions']:
            applied_promotions.append({
                'promotion_id': str(promo_result.promotion.id),
                'promotion_code': promo_result.promotion.code,
                'promotion_name': promo_result.promotion.name,
                'promo_type': promo_result.promotion.promo_type,
                'execution_stage': promo_result.promotion.execution_stage,  # ADD THIS!
                'is_auto_apply': promo_result.promotion.is_auto_apply,      # ADD THIS!
                'discount_amount': float(promo_result.discount_amount),
                'message': promo_result.message,
                'affected_items_count': len(promo_result.affected_items)
            })
        
        return JsonResponse({
            'success': True,
            'subtotal': float(cart.subtotal),
            'discount_amount': float(cart.discount_amount),
            'total': float(cart.total),
            'applied_promotions': applied_promotions,
            'promotions_count': len(applied_promotions)
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def test_clear_cart(request):
    """Clear test cart"""
    request.session['test_cart'] = []
    request.session.modified = True
    
    return JsonResponse({
        'success': True,
        'message': 'Cart cleared'
    })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def test_remove_item(request):
    """Remove item from test cart"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        cart_data = request.session.get('test_cart', [])
        cart_data = [item for item in cart_data if item['product_id'] != product_id]
        
        request.session['test_cart'] = cart_data
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'cart': cart_data
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================
# PROMOTION API ENDPOINTS (for POS)
# ============================================

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def api_calculate_promotions(request):
    """
    API endpoint to calculate promotions for a cart
    Used by POS system
    
    POST /promotions/api/calculate/
    Body: {
        "items": [
            {
                "product_id": "uuid",
                "product_name": "Hot Americano",
                "sku": "001",
                "price": 27000,
                "quantity": 2,
                "category_id": "uuid"
            }
        ],
        "auto_apply_only": true
    }
    """
    try:
        data = json.loads(request.body)
        items_data = data.get('items', [])
        auto_apply_only = data.get('auto_apply_only', True)
        
        if not items_data:
            return JsonResponse({
                'success': False,
                'error': 'No items provided'
            }, status=400)
        
        store_config = Store.get_current()
        brand = store_config.brand
        
        # Build cart items
        cart_items = []
        for item_data in items_data:
            cart_item = CartItem(
                product_id=item_data['product_id'],
                product_name=item_data['product_name'],
                sku=item_data['sku'],
                price=item_data['price'],
                quantity=item_data['quantity'],
                category_id=item_data.get('category_id')
            )
            cart_items.append(cart_item)
        
        # Create cart
        cart = Cart(cart_items, brand, store_config)
        
        # Initialize engine
        engine = PromotionEngine(brand, store_config)
        
        # Apply promotions
        result = engine.apply_promotions_to_cart(cart, auto_apply_only=auto_apply_only)
        
        # Format results
        applied_promotions = []
        for promo_result in result['applied_promotions']:
            applied_promotions.append({
                'promotion_id': str(promo_result.promotion.id),
                'promotion_code': promo_result.promotion.code,
                'promotion_name': promo_result.promotion.name,
                'promo_type': promo_result.promotion.promo_type,
                'discount_amount': float(promo_result.discount_amount),
                'message': promo_result.message,
                'is_stackable': promo_result.promotion.is_stackable,
                'execution_stage': promo_result.promotion.execution_stage
            })
        
        return JsonResponse({
            'success': True,
            'subtotal': float(cart.subtotal),
            'discount_amount': float(cart.discount_amount),
            'total': float(cart.total),
            'applied_promotions': applied_promotions
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@login_required
def api_get_applicable_promotions(request):
    """
    API endpoint to get all applicable promotions
    Used by POS to show available promotions
    
    GET /promotions/api/applicable/
    """
    try:
        store_config = Store.get_current()
        brand = store_config.brand
        
        from django.utils import timezone
        now = timezone.now()
        today = now.date()
        current_time = now.time()
        
        # Get active promotions
        promotions = Promotion.objects.filter(
            brand=brand,
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        ).order_by('execution_priority')
        
        # Filter by time and usage limits
        applicable = []
        for promo in promotions:
            # Check time range
            if promo.time_start and promo.time_end:
                if not (promo.time_start <= current_time <= promo.time_end):
                    continue
            
            # Check usage limits
            if promo.max_uses and promo.current_uses >= promo.max_uses:
                continue
            
            applicable.append({
                'id': str(promo.id),
                'code': promo.code,
                'name': promo.name,
                'description': promo.description,
                'promo_type': promo.promo_type,
                'is_auto_apply': promo.is_auto_apply,
                'is_stackable': promo.is_stackable,
                'execution_stage': promo.execution_stage,
                'execution_priority': promo.execution_priority,
                'rules': promo.get_rules(),
                'scope': promo.get_scope()
            })
        
        return JsonResponse({
            'success': True,
            'promotions': applicable,
            'count': len(applicable)
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

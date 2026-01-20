from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json

from .models import Promotion, Voucher, BillPromotion
from apps.pos.models import Bill


def trigger_client_event(response, event_name, data=None):
    if data:
        response['HX-Trigger'] = json.dumps({event_name: data})
    else:
        response['HX-Trigger'] = event_name
    return response


@login_required
def apply_promo_modal(request, bill_id):
    """Modal to apply promo/voucher - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    auto_promos = Promotion.objects.filter(
        outlet=request.user.outlet,
        is_auto_apply=True,
        is_active=True,
    )
    
    available_promos = [p for p in auto_promos if p.is_valid_now()]
    
    return render(request, 'promotions/partials/apply_promo_modal.html', {
        'bill': bill,
        'available_promos': available_promos,
    })


@login_required
@require_http_methods(["POST"])
def apply_voucher(request, bill_id):
    """Apply voucher code to bill - HTMX"""
    bill = get_object_or_404(Bill, id=bill_id, status='open')
    voucher_code = request.POST.get('voucher_code', '').strip().upper()
    
    try:
        voucher = Voucher.objects.get(code=voucher_code)
    except Voucher.DoesNotExist:
        return HttpResponse(
            '<div class="p-3 bg-red-100 text-red-700 rounded">Voucher tidak ditemukan</div>'
        )
    
    is_valid, message = voucher.is_valid()
    if not is_valid:
        return HttpResponse(f'<div class="p-3 bg-red-100 text-red-700 rounded">{message}</div>')
    
    discount = voucher.promotion.calculate_discount(bill)
    
    if discount <= 0:
        return HttpResponse(
            '<div class="p-3 bg-yellow-100 text-yellow-700 rounded">Voucher tidak berlaku untuk pesanan ini</div>'
        )
    
    success, message = voucher.redeem(bill, request.user)
    if not success:
        return HttpResponse(f'<div class="p-3 bg-red-100 text-red-700 rounded">{message}</div>')
    
    BillPromotion.objects.create(
        bill=bill,
        promotion=voucher.promotion,
        voucher=voucher,
        discount_amount=discount,
        applied_by=request.user,
    )
    
    bill.discount_amount += discount
    bill.calculate_totals()
    
    response = render(request, 'pos/partials/bill_panel.html', {'bill': bill})
    return trigger_client_event(response, 'promoApplied')


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

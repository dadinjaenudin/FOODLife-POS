"""POS services for printing and other operations"""


def print_receipt(bill):
    """Print customer receipt"""
    from apps.kitchen.models import PrinterConfig
    
    config = PrinterConfig.objects.filter(
        outlet=bill.outlet,
        station='cashier',
        is_active=True
    ).first()
    
    if not config:
        print(f"No cashier printer configured for outlet {bill.outlet}")
        return
    
    try:
        from apps.kitchen.services import get_printer
        p = get_printer(config)
        if not p:
            return
        
        # Header
        p.set(align='center', bold=True)
        p.text(f"{bill.outlet.name}\n")
        p.set(bold=False)
        p.text(f"{bill.outlet.address}\n")
        p.text(f"Tel: {bill.outlet.phone}\n")
        p.text("-" * 32 + "\n")
        
        # Bill info
        p.set(align='left')
        p.text(f"No: {bill.bill_number}\n")
        p.text(f"Tanggal: {bill.closed_at.strftime('%d/%m/%Y %H:%M')}\n")
        p.text(f"Kasir: {bill.closed_by.get_full_name() or bill.closed_by.username}\n")
        if bill.table:
            p.text(f"Meja: {bill.table.number}\n")
        if bill.queue_number:
            p.text(f"Antrian: {bill.queue_number}\n")
        p.text("-" * 32 + "\n")
        
        # Items
        for item in bill.items.filter(is_void=False):
            name = item.product.name[:20]
            qty_price = f"{item.quantity}x{item.unit_price:,.0f}"
            total = f"{item.total:,.0f}"
            p.text(f"{name}\n")
            p.text(f"  {qty_price:>15} {total:>10}\n")
        
        p.text("-" * 32 + "\n")
        
        # Totals
        p.text(f"{'Subtotal':20} {bill.subtotal:>10,.0f}\n")
        if bill.discount_amount > 0:
            p.text(f"{'Discount':20} {-bill.discount_amount:>10,.0f}\n")
        p.text(f"{'PPN':20} {bill.tax_amount:>10,.0f}\n")
        p.text(f"{'Service':20} {bill.service_charge:>10,.0f}\n")
        p.set(bold=True, double_height=True)
        p.text(f"{'TOTAL':20} {bill.total:>10,.0f}\n")
        p.set(bold=False, double_height=False)
        
        # Payment
        p.text("-" * 32 + "\n")
        for payment in bill.payments.all():
            p.text(f"{payment.get_method_display():20} {payment.amount:>10,.0f}\n")
        
        # Footer
        p.text("\n")
        p.set(align='center')
        p.text(bill.outlet.receipt_footer or "Terima Kasih!")
        p.text("\n")
        
        p.cut()
        p.close()
        
    except Exception as e:
        print(f"Print error: {e}")

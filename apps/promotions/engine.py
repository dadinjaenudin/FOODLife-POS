"""
Promotion Engine - Calculate and apply promotions to cart
All logic in Python (not JavaScript) for consistency between testing and POS
"""
from decimal import Decimal
from typing import List, Dict, Any, Tuple
from django.utils import timezone
from django.db.models import Q
import json


class CartItem:
    """Represents an item in the cart"""
    def __init__(self, product_id, product_name, sku, price, quantity, category_id=None):
        self.product_id = str(product_id)
        self.product_name = product_name
        self.sku = sku
        self.price = Decimal(str(price))
        self.quantity = int(quantity)
        self.category_id = str(category_id) if category_id else None
        self.subtotal = self.price * self.quantity
        self.applied_promotions = []
        self.discount_amount = Decimal('0')
        self.final_price = self.price
        self.final_subtotal = self.subtotal


class Cart:
    """Represents shopping cart"""
    def __init__(self, items: List[CartItem], brand, store):
        self.items = items
        self.brand = brand
        self.store = store
        self.subtotal = sum(item.subtotal for item in items)
        self.discount_amount = Decimal('0')
        self.total = self.subtotal
        self.applied_promotions = []


class PromotionResult:
    """Result of promotion calculation"""
    def __init__(self, promotion, discount_amount, affected_items=None, message=''):
        self.promotion = promotion
        self.discount_amount = Decimal(str(discount_amount))
        self.affected_items = affected_items or []
        self.message = message
        self.success = discount_amount > 0


class PromotionEngine:
    """
    Main promotion engine - calculates and applies promotions
    """
    
    def __init__(self, brand, store):
        self.brand = brand
        self.store = store
    
    def get_applicable_promotions(self, cart: Cart) -> List:
        """Get all promotions that could apply to this cart"""
        from apps.promotions.models import Promotion
        
        now = timezone.now()
        today = now.date()
        current_time = now.time()
        
        # Get active promotions
        promotions = Promotion.objects.filter(
            brand=self.brand,
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        ).order_by('execution_priority', 'execution_stage')
        
        # Filter by time if specified
        applicable = []
        for promo in promotions:
            # Check time range
            if promo.time_start and promo.time_end:
                if not (promo.time_start <= current_time <= promo.time_end):
                    continue
            
            # Check usage limits
            if promo.max_uses and promo.current_uses >= promo.max_uses:
                continue
            
            # Check if promotion applies to cart items
            if self._promotion_applies_to_cart(promo, cart):
                applicable.append(promo)
        
        return applicable
    
    def _promotion_applies_to_cart(self, promotion, cart: Cart) -> bool:
        """Check if promotion applies to any items in cart"""
        scope = promotion.get_scope()
        apply_to = scope.get('apply_to', 'all')
        
        if apply_to == 'all':
            return True
        
        # Check if any cart item matches scope
        for item in cart.items:
            if self._item_matches_scope(item, scope):
                return True
        
        return False
    
    def _item_matches_scope(self, item: CartItem, scope: Dict) -> bool:
        """Check if item matches promotion scope"""
        apply_to = scope.get('apply_to', 'all')
        
        if apply_to == 'all':
            # Check exclusions
            excluded_products = scope.get('exclude_products', [])
            if item.product_id in excluded_products:
                return False
            
            excluded_categories = scope.get('exclude_categories', [])
            if item.category_id in excluded_categories:
                return False
            
            return True
        
        elif apply_to == 'category':
            categories = scope.get('categories', [])
            return item.category_id in categories
        
        elif apply_to == 'product':
            products = scope.get('products', [])
            return item.product_id in products
        
        return False
    
    def calculate_promotion(self, promotion, cart: Cart) -> PromotionResult:
        """Calculate discount for a specific promotion"""
        promo_type = promotion.promo_type
        
        # Route to specific calculator based on type
        if promo_type == 'percent_discount':
            return self._calculate_percent_discount(promotion, cart)
        elif promo_type == 'amount_discount':
            return self._calculate_amount_discount(promotion, cart)
        elif promo_type == 'buy_x_get_y':
            return self._calculate_buy_x_get_y(promotion, cart)
        elif promo_type == 'combo':
            return self._calculate_combo(promotion, cart)
        elif promo_type == 'free_item':
            return self._calculate_free_item(promotion, cart)
        elif promo_type == 'happy_hour':
            return self._calculate_happy_hour(promotion, cart)
        elif promo_type == 'payment_discount':
            return self._calculate_payment_discount(promotion, cart)
        elif promo_type == 'threshold_tier':
            return self._calculate_threshold_tier(promotion, cart)
        else:
            return PromotionResult(promotion, 0, message=f'Promotion type {promo_type} not implemented yet')
    
    # ============================================
    # PROMOTION TYPE CALCULATORS
    # ============================================
    
    def _calculate_percent_discount(self, promotion, cart: Cart) -> PromotionResult:
        """Calculate percent discount (e.g., 20% off)"""
        rules = promotion.get_rules()
        scope = promotion.get_scope()
        
        discount_percent = Decimal(str(rules.get('discount_percent', 0)))
        max_discount = rules.get('max_discount_amount')
        
        if discount_percent <= 0:
            return PromotionResult(promotion, 0, message='Invalid discount percent')
        
        # Calculate discount on applicable items
        total_discount = Decimal('0')
        affected_items = []
        
        for item in cart.items:
            if self._item_matches_scope(item, scope):
                item_discount = item.subtotal * (discount_percent / 100)
                total_discount += item_discount
                affected_items.append({
                    'item': item,
                    'discount': item_discount
                })
        
        # Apply max discount cap
        if max_discount and total_discount > Decimal(str(max_discount)):
            total_discount = Decimal(str(max_discount))
        
        message = f'{discount_percent}% discount'
        if max_discount:
            message += f' (max Rp {max_discount:,.0f})'
        
        return PromotionResult(promotion, total_discount, affected_items, message)
    
    def _calculate_amount_discount(self, promotion, cart: Cart) -> PromotionResult:
        """Calculate fixed amount discount (e.g., Rp 10,000 off)"""
        rules = promotion.get_rules()
        scope = promotion.get_scope()
        
        discount_amount = Decimal(str(rules.get('discount_amount', 0)))
        min_purchase = rules.get('min_purchase_amount', 0)
        
        if discount_amount <= 0:
            return PromotionResult(promotion, 0, message='Invalid discount amount')
        
        # Check minimum purchase
        if min_purchase and cart.subtotal < Decimal(str(min_purchase)):
            return PromotionResult(
                promotion, 0, 
                message=f'Minimum purchase Rp {min_purchase:,.0f} required'
            )
        
        # Calculate applicable subtotal
        applicable_subtotal = Decimal('0')
        affected_items = []
        
        for item in cart.items:
            if self._item_matches_scope(item, scope):
                applicable_subtotal += item.subtotal
                affected_items.append({'item': item})
        
        if applicable_subtotal == 0:
            return PromotionResult(promotion, 0, message='No applicable items')
        
        # Discount cannot exceed applicable subtotal
        final_discount = min(discount_amount, applicable_subtotal)
        
        message = f'Rp {discount_amount:,.0f} discount'
        
        return PromotionResult(promotion, final_discount, affected_items, message)
    
    def _calculate_buy_x_get_y(self, promotion, cart: Cart) -> PromotionResult:
        """Calculate Buy X Get Y discount (e.g., Buy 2 Get 1 Free)"""
        rules = promotion.get_rules()
        scope = promotion.get_scope()
        
        buy_qty = int(rules.get('buy_quantity', 0))
        get_qty = int(rules.get('get_quantity', 0))
        get_discount_percent = Decimal(str(rules.get('get_discount_percent', 100)))  # 100 = free
        
        if buy_qty <= 0 or get_qty <= 0:
            return PromotionResult(promotion, 0, message='Invalid buy/get quantities')
        
        # Get applicable items sorted by price (cheapest gets discount)
        applicable_items = [
            item for item in cart.items 
            if self._item_matches_scope(item, scope)
        ]
        
        if not applicable_items:
            return PromotionResult(promotion, 0, message='No applicable items')
        
        # Calculate total quantity
        total_qty = sum(item.quantity for item in applicable_items)
        
        # Calculate how many sets qualify
        required_qty = buy_qty + get_qty
        num_sets = total_qty // required_qty
        
        if num_sets == 0:
            return PromotionResult(
                promotion, 0,
                message=f'Buy {buy_qty} get {get_qty} - need {required_qty} items'
            )
        
        # Sort items by price (ascending) - cheapest items get discount
        sorted_items = sorted(applicable_items, key=lambda x: x.price)
        
        # Calculate discount on cheapest items
        total_discount = Decimal('0')
        free_items_count = num_sets * get_qty
        affected_items = []
        
        for item in sorted_items:
            if free_items_count <= 0:
                break
            
            discount_qty = min(item.quantity, free_items_count)
            item_discount = item.price * discount_qty * (get_discount_percent / 100)
            total_discount += item_discount
            free_items_count -= discount_qty
            
            affected_items.append({
                'item': item,
                'discount_qty': discount_qty,
                'discount': item_discount
            })
        
        message = f'Buy {buy_qty} Get {get_qty}'
        if get_discount_percent < 100:
            message += f' ({get_discount_percent}% off)'
        else:
            message += ' Free'
        
        return PromotionResult(promotion, total_discount, affected_items, message)
    
    def _calculate_combo(self, promotion, cart: Cart) -> PromotionResult:
        """Calculate combo deal (e.g., 3 items for special price)"""
        rules = promotion.get_rules()
        scope = promotion.get_scope()
        
        required_qty = int(rules.get('required_quantity', 0))
        combo_price = Decimal(str(rules.get('combo_price', 0)))
        
        if required_qty <= 0 or combo_price <= 0:
            return PromotionResult(promotion, 0, message='Invalid combo configuration')
        
        # Get applicable items
        applicable_items = [
            item for item in cart.items 
            if self._item_matches_scope(item, scope)
        ]
        
        if not applicable_items:
            return PromotionResult(promotion, 0, message='No applicable items')
        
        # Calculate total quantity
        total_qty = sum(item.quantity for item in applicable_items)
        
        # Calculate how many combos qualify
        num_combos = total_qty // required_qty
        
        if num_combos == 0:
            return PromotionResult(
                promotion, 0,
                message=f'Need {required_qty} items for combo'
            )
        
        # Calculate normal price for combo items
        normal_price_per_combo = sum(
            item.price * min(item.quantity, required_qty)
            for item in applicable_items
        )
        
        # Calculate discount
        total_discount = (normal_price_per_combo - combo_price) * num_combos
        
        if total_discount < 0:
            total_discount = Decimal('0')
        
        message = f'{required_qty} items for Rp {combo_price:,.0f}'
        
        return PromotionResult(promotion, total_discount, applicable_items, message)
    
    def _calculate_free_item(self, promotion, cart: Cart) -> PromotionResult:
        """Calculate free item promotion"""
        rules = promotion.get_rules()
        
        min_purchase = Decimal(str(rules.get('min_purchase_amount', 0)))
        free_product_id = rules.get('free_product_id')
        free_product_price = Decimal(str(rules.get('free_product_price', 0)))
        
        if cart.subtotal < min_purchase:
            return PromotionResult(
                promotion, 0,
                message=f'Minimum purchase Rp {min_purchase:,.0f} required'
            )
        
        # Check if free item is in cart
        has_free_item = any(
            item.product_id == free_product_id 
            for item in cart.items
        )
        
        if not has_free_item:
            return PromotionResult(
                promotion, 0,
                message='Add free item to cart to claim'
            )
        
        message = f'Free item (worth Rp {free_product_price:,.0f})'
        
        return PromotionResult(promotion, free_product_price, [], message)
    
    def _calculate_happy_hour(self, promotion, cart: Cart) -> PromotionResult:
        """Calculate happy hour discount (time-based)"""
        # Similar to percent_discount but time-restricted
        return self._calculate_percent_discount(promotion, cart)
    
    def _calculate_payment_discount(self, promotion, cart: Cart) -> PromotionResult:
        """Calculate payment method discount"""
        rules = promotion.get_rules()
        
        discount_percent = Decimal(str(rules.get('discount_percent', 0)))
        max_discount = rules.get('max_discount_amount')
        payment_methods = rules.get('payment_methods', [])
        
        # This will be applied at payment stage
        # For now, just calculate potential discount
        discount = cart.subtotal * (discount_percent / 100)
        
        if max_discount and discount > Decimal(str(max_discount)):
            discount = Decimal(str(max_discount))
        
        message = f'{discount_percent}% off with {", ".join(payment_methods)}'
        
        return PromotionResult(promotion, discount, [], message)
    
    def _calculate_threshold_tier(self, promotion, cart: Cart) -> PromotionResult:
        """Calculate tiered discount (spend more, save more)"""
        rules = promotion.get_rules()
        tiers = rules.get('tiers', [])
        
        if not tiers:
            return PromotionResult(promotion, 0, message='No tiers configured')
        
        # Sort tiers by threshold descending
        sorted_tiers = sorted(
            tiers, 
            key=lambda x: x.get('threshold', 0), 
            reverse=True
        )
        
        # Find applicable tier
        applicable_tier = None
        for tier in sorted_tiers:
            threshold = Decimal(str(tier.get('threshold', 0)))
            if cart.subtotal >= threshold:
                applicable_tier = tier
                break
        
        if not applicable_tier:
            # Show next tier
            next_tier = sorted_tiers[-1]
            next_threshold = Decimal(str(next_tier.get('threshold', 0)))
            remaining = next_threshold - cart.subtotal
            return PromotionResult(
                promotion, 0,
                message=f'Spend Rp {remaining:,.0f} more to get discount'
            )
        
        # Calculate discount based on tier type
        discount_type = applicable_tier.get('discount_type', 'percent')
        
        if discount_type == 'percent':
            discount_percent = Decimal(str(applicable_tier.get('discount_percent', 0)))
            discount = cart.subtotal * (discount_percent / 100)
            message = f'{discount_percent}% off (tier discount)'
        else:
            discount = Decimal(str(applicable_tier.get('discount_amount', 0)))
            message = f'Rp {discount:,.0f} off (tier discount)'
        
        return PromotionResult(promotion, discount, [], message)
    
    def apply_promotions_to_cart(self, cart: Cart, auto_apply_only=True) -> Dict[str, Any]:
        """
        Apply all applicable promotions to cart
        Returns summary of applied promotions
        """
        applicable_promotions = self.get_applicable_promotions(cart)
        
        if auto_apply_only:
            applicable_promotions = [
                p for p in applicable_promotions 
                if p.is_auto_apply
            ]
        
        applied_results = []
        total_discount = Decimal('0')
        
        for promotion in applicable_promotions:
            result = self.calculate_promotion(promotion, cart)
            
            if result.success:
                applied_results.append(result)
                total_discount += result.discount_amount
                
                # Check if stackable
                if not promotion.is_stackable:
                    break  # Stop after first non-stackable promotion
        
        # Update cart totals
        cart.discount_amount = total_discount
        cart.total = cart.subtotal - total_discount
        cart.applied_promotions = applied_results
        
        return {
            'success': True,
            'cart': cart,
            'applied_promotions': applied_results,
            'total_discount': total_discount,
            'final_total': cart.total
        }

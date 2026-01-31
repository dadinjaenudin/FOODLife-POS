"""
Recommendation Engine for QR Order
Provides product recommendations based on various algorithms
"""
from django.db.models import Count, Sum, Q
from collections import defaultdict
from datetime import timedelta
from django.utils import timezone

from apps.pos.models import Bill, BillItem
from apps.core.models import Product


class RecommendationEngine:
    """Product recommendation system"""
    
    def __init__(self, brand_id):
        self.brand_id = brand_id
        
    def get_popular_items(self, limit=6, days=30):
        """
        Get most popular items based on order frequency
        
        Args:
            limit: Number of items to return
            days: Look back period in days
            
        Returns:
            List of Product objects
        """
        since_date = timezone.now() - timedelta(days=days)
        
        popular_products = BillItem.objects.filter(
            bill__brand_id=self.brand_id,
            bill__created_at__gte=since_date,
            is_void=False
        ).values('product').annotate(
            order_count=Count('id'),
            total_quantity=Sum('quantity')
        ).order_by('-order_count')[:limit]
        
        product_ids = [item['product'] for item in popular_products]
        
        # Get products maintaining order
        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True
        )
        
        # Sort by original order
        product_dict = {p.id: p for p in products}
        return [product_dict[pid] for pid in product_ids if pid in product_dict]
    
    def get_frequently_bought_together(self, product_id, limit=4):
        """
        Find products frequently bought together with given product
        Uses co-occurrence in bills
        
        Args:
            product_id: The product to find companions for
            limit: Number of recommendations
            
        Returns:
            List of (Product, score) tuples
        """
        # Get bills containing the target product (last 60 days)
        since_date = timezone.now() - timedelta(days=60)
        
        bills_with_product = Bill.objects.filter(
            brand_id=self.brand_id,
            items__product_id=product_id,
            items__is_void=False,
            created_at__gte=since_date,
            status__in=['paid', 'open']
        ).values_list('id', flat=True)
        
        # Count co-occurrences
        co_occurrences = BillItem.objects.filter(
            bill_id__in=bills_with_product,
            is_void=False
        ).exclude(
            product_id=product_id
        ).values('product').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]
        
        product_ids = [item['product'] for item in co_occurrences]
        
        # Get products with scores
        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True
        )
        
        # Create score mapping
        score_map = {item['product']: item['count'] for item in co_occurrences}
        
        recommendations = [
            (product, score_map[product.id]) 
            for product in products 
            if product.id in score_map
        ]
        
        return sorted(recommendations, key=lambda x: x[1], reverse=True)
    
    def get_category_recommendations(self, category_id, exclude_product_id=None, limit=6):
        """
        Get popular products from the same category
        
        Args:
            category_id: Category to get recommendations from
            exclude_product_id: Product to exclude (current product)
            limit: Number of recommendations
            
        Returns:
            List of Product objects
        """
        since_date = timezone.now() - timedelta(days=30)
        
        # Get popular products in same category
        query = BillItem.objects.filter(
            bill__brand_id=self.brand_id,
            product__category_id=category_id,
            product__is_active=True,
            bill__created_at__gte=since_date,
            is_void=False
        )
        
        if exclude_product_id:
            query = query.exclude(product_id=exclude_product_id)
        
        popular_in_category = query.values('product').annotate(
            order_count=Count('id')
        ).order_by('-order_count')[:limit]
        
        product_ids = [item['product'] for item in popular_in_category]
        
        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True
        )
        
        # Maintain order
        product_dict = {p.id: p for p in products}
        return [product_dict[pid] for pid in product_ids if pid in product_dict]
    
    def get_recommended_for_cart(self, cart_product_ids, limit=6):
        """
        Get recommendations based on current cart contents
        Finds products that are frequently bought with items in cart
        
        Args:
            cart_product_ids: List of product IDs currently in cart
            limit: Number of recommendations
            
        Returns:
            List of Product objects
        """
        if not cart_product_ids:
            return self.get_popular_items(limit=limit)
        
        since_date = timezone.now() - timedelta(days=60)
        
        # Find bills containing any cart products
        bills_with_cart_items = Bill.objects.filter(
            brand_id=self.brand_id,
            items__product_id__in=cart_product_ids,
            items__is_void=False,
            created_at__gte=since_date,
            status__in=['paid', 'open']
        ).values_list('id', flat=True)
        
        # Count co-occurrences (products in those bills)
        recommendations = BillItem.objects.filter(
            bill_id__in=bills_with_cart_items,
            is_void=False
        ).exclude(
            product_id__in=cart_product_ids
        ).values('product').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]
        
        product_ids = [item['product'] for item in recommendations]
        
        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True
        )
        
        # Maintain order
        product_dict = {p.id: p for p in products}
        return [product_dict[pid] for pid in product_ids if pid in product_dict]
    
    def get_trending_items(self, limit=6, days=7):
        """
        Get trending items (items with increasing popularity)
        
        Args:
            limit: Number of items to return
            days: Recent period to check
            
        Returns:
            List of Product objects
        """
        recent_date = timezone.now() - timedelta(days=days)
        older_date = timezone.now() - timedelta(days=days*2)
        
        # Recent period orders
        recent_orders = BillItem.objects.filter(
            bill__brand_id=self.brand_id,
            bill__created_at__gte=recent_date,
            is_void=False
        ).values('product').annotate(
            recent_count=Count('id')
        )
        
        # Older period orders
        older_orders = BillItem.objects.filter(
            bill__brand_id=self.brand_id,
            bill__created_at__gte=older_date,
            bill__created_at__lt=recent_date,
            is_void=False
        ).values('product').annotate(
            older_count=Count('id')
        )
        
        # Calculate growth
        recent_dict = {item['product']: item['recent_count'] for item in recent_orders}
        older_dict = {item['product']: item['older_count'] for item in older_orders}
        
        trending = []
        for product_id, recent_count in recent_dict.items():
            older_count = older_dict.get(product_id, 0)
            if older_count > 0:
                growth = (recent_count - older_count) / older_count
            else:
                growth = recent_count  # New products get high growth
            
            if growth > 0:  # Only growing products
                trending.append((product_id, growth, recent_count))
        
        # Sort by growth, but prefer items with decent volume
        trending.sort(key=lambda x: (x[1] * x[2]), reverse=True)
        
        product_ids = [item[0] for item in trending[:limit]]
        
        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True
        )
        
        product_dict = {p.id: p for p in products}
        return [product_dict[pid] for pid in product_ids if pid in product_dict]

# Floor Plan System - Technical Documentation
**Updated:** 2026-01-26  
**Version:** 2.0

---

## 📋 Table of Contents
1. [Overview](#overview)
2. [Recent Updates](#recent-updates)
3. [Database Schema](#database-schema)
4. [Model Changes](#model-changes)
5. [Views & Logic](#views--logic)
6. [Template Structure](#template-structure)
7. [Frontend Features](#frontend-features)
8. [Auto-Positioning Logic](#auto-positioning-logic)
9. [Drag & Drop Implementation](#drag--drop-implementation)
10. [Best Practices](#best-practices)

---

## 🎯 Overview

The Floor Plan System provides restaurant table management with:
- ✅ **Visual floor plan editor** with drag & drop
- ✅ **Real-time table positioning**
- ✅ **Auto-layout algorithms**
- ✅ **Circular table design** (matching enhanced view)
- ✅ **Synchronized views** (Enhanced & Floor Plan Overview)

---

## 🆕 Recent Updates (v2.0)

### **1. Model Rename: `Table` → `Tables`**
**Date:** 2026-01-26  
**Reason:** Avoid SQL reserved keyword conflict

**Changes:**
- Model class: `Table` → `Tables`
- Database table: `table` → `tables`
- All references updated across codebase

**Migration:** `0011_rename_table_to_tables.py`

```python
operations = [
    migrations.RenameModel(
        old_name='Table',
        new_name='Tables',
    ),
    migrations.AlterModelTable(
        name='Tables',
        table='tables',
    ),
]
```

### **2. Floor Plan Synchronization**
**Issue:** Floor plan positions not matching enhanced view  
**Solution:** Unified auto-positioning logic across both views

**Before:**
```django
{# Different auto-position logic #}
style="left: {% cycle 50 200 350 500 %}px; top: {% cycle 100 250 400 %}px;"
```

**After:**
```django
{# Matching enhanced view logic: 50 + index*80, 100 + floor(index/8)*80 #}
style="left: {% widthratio forloop.counter0 1 80 %}px; top: {% widthratio forloop.counter0 8 80 %}px; margin-left: 50px; margin-top: 100px;"
```

### **3. Manual Position Handling**
**Fixed:** Extra offset applied to manually positioned tables

**Before:**
```django
style="left: {{ pos_x|add:50 }}px; top: {{ pos_y|add:100 }}px;"
```

**After:**
```django
style="left: {{ pos_x }}px; top: {{ pos_y }}px;"
```

### **4. Table Shape Standardization**
**Changed:** All views now use circular tables

```html
<!-- Enhanced View & Floor Plan -->
<div class="w-16 h-16 rounded-full ...">
```

### **5. Auto-Refresh After Table Operations**
**Added:** Page reload after create/update/delete table

**Backend:**
```python
return JsonResponse({
    'success': True,
    'message': f'Table {number} created successfully',
    'reload': True  # Trigger page reload
})
```

**Frontend:**
```javascript
if (data.reload) {
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}
```

---

## 🗄️ Database Schema

### **Tables Model** (Renamed from `Table`)

```python
class Tables(models.Model):
    """
    Individual tables in restaurant
    Named 'Tables' (plural) to avoid SQL reserved keyword conflict
    """
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    area = models.ForeignKey(TableArea, on_delete=models.PROTECT, related_name='tables')
    number = models.CharField(max_length=20)
    capacity = models.IntegerField(validators=[MinValueValidator(1)])
    qr_code = models.CharField(max_length=200, blank=True)
    
    # Floor plan positioning
    pos_x = models.IntegerField(null=True, blank=True)
    pos_y = models.IntegerField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tables'  # Changed from 'table'
        verbose_name = 'Table'
        verbose_name_plural = 'Tables'
        ordering = ['area', 'number']
```

### **TableArea Model**

```python
class TableArea(models.Model):
    """
    Areas/sections in restaurant (e.g., Indoor, Outdoor, VIP)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT)
    store = models.ForeignKey(Store, on_delete=models.PROTECT, null=True, blank=True)
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)
    
    # Floor plan dimensions
    floor_width = models.IntegerField(default=1200)
    floor_height = models.IntegerField(default=800)
    floor_image = models.ImageField(upload_to='floor_plans/', blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

---

## 🔧 Views & Logic

### **Enhanced TableArea View**

**File:** `products/views/enhanced_tablearea_views.py`

```python
def floor_plan_overview(request):
    """
    Floor Plan Overview - Show all table areas with their tables
    """
    # Get store from session
    store_id = request.session.get('global_store_id')
    if not store_id:
        return redirect('tablearea:list')
    
    # Get all table areas for this store
    tableareas = TableArea.objects.filter(
        store_id=store_id,
        is_active=True
    ).select_related('brand', 'store', 'company').order_by('sort_order', 'name')
    
    # Add table counts and status info for each area
    enhanced_areas = []
    for area in tableareas:
        tables = area.tables.filter(is_active=True)
        
        # Count tables by status
        available_count = tables.filter(status='available').count()
        occupied_count = tables.filter(status='occupied').count() 
        reserved_count = tables.filter(status='reserved').count()
        total_capacity = tables.aggregate(total=Sum('capacity'))['total'] or 0
        
        # Add stats to area object
        area.table_count = tables.count()
        area.available_count = available_count
        area.occupied_count = occupied_count
        area.reserved_count = reserved_count
        area.total_capacity = total_capacity
        
        # IMPORTANT: Pass filtered tables to template
        area.active_tables = list(tables)
        
        enhanced_areas.append(area)
    
    context = {
        'tableareas': enhanced_areas,
        'total_areas': len(enhanced_areas),
        'total_tables': sum(a.table_count for a in enhanced_areas),
        'total_capacity': sum(a.total_capacity for a in enhanced_areas),
    }
    
    return render(request, 'products/tablearea/floor_plan.html', context)
```

### **Table CRUD Operations**

```python
@login_required
@require_POST
def create_table(request):
    """Create new table with auto-refresh"""
    # ... validation and creation logic ...
    
    table = Tables.objects.create(
        area=area,
        number=number,
        capacity=capacity,
        pos_x=pos_x,
        pos_y=pos_y,
        status=status,
        is_active=is_active,
        qr_code=f'QR-{area.store.store_name}-{area.name}-{number}'
    )
    
    response = JsonResponse({
        'success': True,
        'message': f'Table {number} created successfully',
        'table': {
            'id': str(table.id),
            'number': table.number,
            'capacity': table.capacity,
            'pos_x': table.pos_x,
            'pos_y': table.pos_y,
            'status': table.status,
        },
        'reload': True  # Trigger page reload to update stats
    })
    
    return response
```

---

## 🎨 Template Structure

### **Floor Plan Overview Template**

**File:** `templates/products/tablearea/floor_plan.html`

```django
{% for tablearea in tableareas %}
<div class="floor-plan-section">
    <h3>{{ tablearea.name }}</h3>
    
    <!-- Floor Plan Canvas -->
    <div class="relative bg-gray-50 rounded-lg p-6 min-h-[600px]">
        {% for table in tablearea.active_tables %}
        
        {% with pos_x=table.pos_x|default:0 pos_y=table.pos_y|default:0 %}
        {% if pos_x == 0 and pos_y == 0 %}
            {# AUTO-POSITION: Matching enhanced view logic #}
            <div class="absolute table-item"
                 style="left: {% widthratio forloop.counter0 1 80 %}px; 
                        top: {% widthratio forloop.counter0 8 80 %}px; 
                        margin-left: 50px; 
                        margin-top: 100px;">
        {% else %}
            {# EXACT POSITION: Use database coordinates #}
            <div class="absolute table-item"
                 style="left: {{ pos_x }}px; top: {{ pos_y }}px;">
        {% endif %}
        {% endwith %}
        
                <!-- Circular Table -->
                <div class="w-16 h-16 rounded-full border-3 flex items-center justify-center 
                            shadow-lg {% if table.status == 'available' %}bg-green-500{% elif table.status == 'occupied' %}bg-red-500{% else %}bg-yellow-500{% endif %}">
                    <span class="text-white font-bold text-sm">{{ table.number }}</span>
                </div>
                
                <!-- Capacity Badge -->
                <div class="capacity-badge">
                    <i class="fas fa-users"></i> {{ table.capacity }}
                </div>
            </div>
        {% endfor %}
    </div>
</div>
{% endfor %}
```

### **Enhanced List Template**

**File:** `templates/products/tablearea/enhanced_list.html`

**Key Features:**
- Drag & drop repositioning
- Auto-save position on drop
- Synchronized with floor plan view

```javascript
// Auto-Position Logic (Matching Floor Plan)
:style="`left: ${table.pos_x || (50 + tables.indexOf(table) * 80)}px; 
         top: ${table.pos_y || (100 + Math.floor(tables.indexOf(table) / 8) * 80)}px;`"
```

---

## 🧮 Auto-Positioning Logic

### **Formula**

For tables with `pos_x=0` and `pos_y=0`:

```
X Position: 50 + (index * 80)
Y Position: 100 + (floor(index / 8) * 80)
```

### **Grid Layout**

- **8 tables per row** (8 columns)
- **Horizontal spacing:** 80px
- **Vertical spacing:** 80px
- **Starting offset:** (50px, 100px)

### **Example Positions**

| Index | X Position | Y Position | Grid Position |
|-------|------------|------------|---------------|
| 0 | 50 | 100 | Row 1, Col 1 |
| 1 | 130 | 100 | Row 1, Col 2 |
| 2 | 210 | 100 | Row 1, Col 3 |
| 7 | 610 | 100 | Row 1, Col 8 |
| 8 | 50 | 180 | Row 2, Col 1 |
| 9 | 130 | 180 | Row 2, Col 2 |

### **Implementation**

**Django Template (Floor Plan):**
```django
{% widthratio forloop.counter0 1 80 %}px  {# X: index * 80 #}
{% widthratio forloop.counter0 8 80 %}px  {# Y: floor(index/8) * 80 #}
margin-left: 50px;  {# X offset #}
margin-top: 100px;  {# Y offset #}
```

**JavaScript (Enhanced View):**
```javascript
const x = table.pos_x || (50 + tables.indexOf(table) * 80);
const y = table.pos_y || (100 + Math.floor(tables.indexOf(table) / 8) * 80);
```

---

## 🖱️ Drag & Drop Implementation

### **Frontend (Alpine.js)**

```javascript
function tableAreaManager() {
    return {
        draggedTable: null,
        isDragging: false,
        dragOffset: { x: 0, y: 0 },
        
        startDrag(event, table) {
            this.isDragging = true;
            this.draggedTable = table;
            
            const rect = event.target.getBoundingClientRect();
            this.dragOffset = {
                x: event.clientX - rect.left,
                y: event.clientY - rect.top
            };
        },
        
        handleDrag(event) {
            if (!this.draggedTable || !this.isDragging) return;
            
            const container = event.currentTarget;
            const rect = container.getBoundingClientRect();
            
            // Calculate new position
            const newX = Math.max(0, Math.min(
                event.clientX - rect.left - this.dragOffset.x, 
                this.floorPlanWidth - 64
            ));
            const newY = Math.max(0, Math.min(
                event.clientY - rect.top - this.dragOffset.y, 
                this.floorPlanHeight - 64
            ));
            
            // Update table position
            this.draggedTable.pos_x = Math.round(newX);
            this.draggedTable.pos_y = Math.round(newY);
        },
        
        stopDrag() {
            if (this.draggedTable) {
                this.saveTablePosition(this.draggedTable);
                this.draggedTable = null;
            }
            this.isDragging = false;
        },
        
        saveTablePosition(table) {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            fetch('/products/tableareas/tables/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({
                    table_id: table.id,
                    number: table.number,
                    capacity: table.capacity,
                    pos_x: table.pos_x,
                    pos_y: table.pos_y
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showToastMessage(`Table ${table.number} position saved!`, 'success');
                }
            });
        }
    }
}
```

---

## 📊 Best Practices

### **1. Position Management**

✅ **DO:**
- Use `pos_x=0, pos_y=0` as default for new tables
- Let auto-positioning handle initial layout
- Save positions immediately after drag & drop
- Validate position bounds before saving

❌ **DON'T:**
- Hard-code positions in backend
- Apply extra offsets to manual positions
- Mix auto-position and manual position logic

### **2. View Synchronization**

✅ **DO:**
- Use identical auto-position formula across all views
- Pass `active_tables` list to templates
- Filter inactive tables in backend, not frontend
- Reload page after CRUD operations to sync stats

❌ **DON'T:**
- Use different formulas in different views
- Rely on `tablearea.tables.all` without filtering
- Trust frontend-only stats

### **3. Model Naming**

✅ **DO:**
- Avoid SQL reserved keywords (table, order, user, group)
- Use plural names for clarity (Tables, Orders, Users)
- Document reason for unusual naming

❌ **DON'T:**
- Use SQL keywords as model names
- Change naming convention mid-project without migration

### **4. Frontend Performance**

✅ **DO:**
- Use CSS transforms for smooth dragging
- Debounce position save operations
- Show loading states during operations
- Use toast notifications for feedback

❌ **DON'T:**
- Update database on every mouse move
- Block UI during save operations
- Silently fail without user feedback

---

## 🚀 Future Enhancements

### **Planned Features**

1. **Multi-Select Drag**
   - Select multiple tables
   - Move as group
   - Maintain relative positions

2. **Snap to Grid**
   - Optional grid snapping
   - Configurable grid size
   - Visual grid overlay

3. **Undo/Redo**
   - Position history
   - Revert changes
   - Batch operations

4. **Floor Plan Templates**
   - Pre-defined layouts
   - Quick setup for new stores
   - Layout library

5. **Real-Time Collaboration**
   - WebSocket updates
   - Multi-user editing
   - Conflict resolution

---

## 📝 Changelog

### **Version 2.0** (2026-01-26)
- ✅ Renamed `Table` model to `Tables` to avoid SQL keyword conflict
- ✅ Fixed floor plan positioning synchronization
- ✅ Standardized circular table design across all views
- ✅ Removed extra offsets for manual positions
- ✅ Added auto-refresh after table operations
- ✅ Unified auto-positioning logic

### **Version 1.0** (Previous)
- Initial floor plan implementation
- Basic drag & drop functionality
- Table status management
- Multi-view support

---

## 🔗 Related Files

- **Models:** `products/models.py`
- **Views:** `products/views/enhanced_tablearea_views.py`
- **Templates:** 
  - `templates/products/tablearea/floor_plan.html`
  - `templates/products/tablearea/enhanced_list.html`
- **Migrations:** `products/migrations/0011_rename_table_to_tables.py`
- **API:** `products/api/views.py`, `products/api/serializers.py`

---

## 📞 Support

For questions or issues related to the floor plan system:
1. Check this documentation
2. Review code comments in related files
3. Test in development environment first
4. Document any bugs or improvements

---

**Last Updated:** 2026-01-26  
**Maintained By:** Development Team  
**Status:** ✅ Production Ready

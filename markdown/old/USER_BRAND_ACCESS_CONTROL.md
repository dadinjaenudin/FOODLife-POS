# User Brand Access Control
## Kasir/User Assignment ke Brands

## 🎯 Requirement

**Scenario:**
- 1 Store punya multiple brands (CHICKEN SUMO, NASI PADANG, SOTO)
- User A bisa akses CHICKEN SUMO + NASI PADANG
- User B hanya bisa akses SOTO LAMONGAN
- User C (Manager) bisa akses semua brands

## 🏗️ Architecture Solution

### Current User Model
```python
class POSUser(AbstractUser):
    """Current model (assumed)"""
    username = models.CharField(max_length=150, unique=True)
    pin = models.CharField(max_length=6)
    role = models.CharField(max_length=20)
    # Missing: brand assignment!
```

### Proposed: Add User-Brand Assignment

**Option 1: Many-to-Many (RECOMMENDED)**
```python
class POSUser(AbstractUser):
    username = models.CharField(max_length=150, unique=True)
    pin = models.CharField(max_length=6)
    role = models.CharField(max_length=20)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)  # User belongs to store
    brands = models.ManyToManyField(Brand, through='UserBrand')  # Can access multiple brands

class UserBrand(models.Model):
    """User access to specific brands"""
    user = models.ForeignKey(POSUser, on_delete=models.CASCADE, related_name='user_brands')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='brand_users')
    can_login = models.BooleanField(default=True)
    can_void = models.BooleanField(default=False)  # Brand-specific permissions
    can_discount = models.BooleanField(default=False)
    is_manager = models.BooleanField(default=False)
    
    class Meta:
        unique_together = [['user', 'brand']]
        verbose_name = 'User Brand Access'
```

**Option 2: Single Brand per User (Simpler)**
```python
class POSUser(AbstractUser):
    username = models.CharField(max_length=150, unique=True)
    pin = models.CharField(max_length=6)
    role = models.CharField(max_length=20)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)  # User assigned to 1 brand
    
    # Limitation: User can only work at 1 brand
```

## 📊 Database Design (Option 1 - Recommended)

### Users Table
```sql
user_id  | username | pin  | role     | store_id
---------|----------|------|----------|----------
user-1   | alice    | 1234 | CASHIER  | store-1
user-2   | bob      | 5678 | CASHIER  | store-1
user-3   | charlie  | 9999 | MANAGER  | store-1
```

### UserBrand Table (Many-to-Many)
```sql
id    | user_id | brand_id      | can_login | can_void | can_discount | is_manager
------|---------|---------------|-----------|----------|--------------|------------
ub-1  | user-1  | CHICKEN_SUMO  | true      | false    | false        | false
ub-2  | user-1  | NASI_PADANG   | true      | false    | false        | false
ub-3  | user-2  | SOTO_LAMONGAN | true      | false    | false        | false
ub-4  | user-3  | CHICKEN_SUMO  | true      | true     | true         | true
ub-5  | user-3  | NASI_PADANG   | true      | true     | true         | true
ub-6  | user-3  | SOTO_LAMONGAN | true      | true     | true         | true
```

**Explanation:**
- Alice (user-1) can work at CHICKEN SUMO and NASI PADANG
- Bob (user-2) can only work at SOTO LAMONGAN
- Charlie (user-3) is manager, can access all brands with elevated permissions

## 🔐 Login & Brand Selection Flow

### Flow 1: Login → Select Brand

```
1. User enters PIN at terminal
   ├─ System validates PIN
   └─ Get user's accessible brands

2. If user has multiple brands:
   ├─ Show brand selection screen
   ├─ User selects brand (e.g., CHICKEN SUMO)
   └─ Session locked to that brand

3. If user has only 1 brand:
   ├─ Auto-select that brand
   └─ Go directly to POS

4. Start work session
   ├─ User: Alice
   ├─ Terminal: T01-SUMO
   ├─ Brand: CHICKEN SUMO
   └─ Store: YOGYA SUNDA
```

### Flow 2: Terminal-Based Brand Lock

```
1. Terminal registered to specific brand (T01-SUMO → CHICKEN SUMO)
2. User logs in at T01-SUMO
3. System validates:
   ├─ Does user have access to CHICKEN SUMO?
   ├─ Yes: Allow login
   └─ No: Deny login with message "You don't have access to this brand"
4. User automatically works in CHICKEN SUMO context
```

## 🎨 UI Design

### User Management Screen

```
┌────────────────────────────────────────────────────────────┐
│                    Manage Users                            │
├────────────────────────────────────────────────────────────┤
│  User: Alice                                               │
│  PIN: [1234]                                               │
│  Role: [Cashier ▼]                                        │
│                                                            │
│  Brand Access:                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ ☑ CHICKEN SUMO                                        │ │
│  │   Permissions: [✓] Login  [ ] Void  [ ] Discount     │ │
│  │                                                        │ │
│  │ ☑ NASI PADANG                                         │ │
│  │   Permissions: [✓] Login  [ ] Void  [ ] Discount     │ │
│  │                                                        │ │
│  │ ☐ SOTO LAMONGAN                                       │ │
│  │   Permissions: [ ] Login  [ ] Void  [ ] Discount     │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  [💾 Save User]                                           │
└────────────────────────────────────────────────────────────┘
```

### Login Screen (Multi-Brand User)

```
┌────────────────────────────────────────────────────────────┐
│                    Welcome, Alice!                         │
├────────────────────────────────────────────────────────────┤
│  Select Brand to Work With:                                │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  🍗 CHICKEN SUMO                                      │ │
│  │     Terminal: T01-SUMO, T02-SUMO                     │ │
│  │     [Select →]                                        │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  🍛 NASI PADANG                                       │ │
│  │     Terminal: T03-PADANG                             │ │
│  │     [Select →]                                        │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### POS Header (Shows Current Brand)

```
┌────────────────────────────────────────────────────────────┐
│ 🍗 CHICKEN SUMO | Terminal: T01-SUMO | Cashier: Alice     │
│ Store: YOGYA SUNDA | Session: #12345                      │
├────────────────────────────────────────────────────────────┤
│  [Products only from CHICKEN SUMO brand]                   │
└────────────────────────────────────────────────────────────┘
```

## 🔒 Access Control Logic

### Login Validation

```python
def validate_user_brand_access(user, terminal):
    """Check if user can login to this terminal"""
    
    terminal_brand = terminal.brand
    
    # Check if user has access to terminal's brand
    has_access = UserBrand.objects.filter(
        user=user,
        brand=terminal_brand,
        can_login=True
    ).exists()
    
    if not has_access:
        raise PermissionDenied(
            f"You don't have access to {terminal_brand.name}. "
            f"Please contact your manager."
        )
    
    return True
```

### Brand Selection (Multi-Brand User)

```python
def get_user_accessible_brands(user, store):
    """Get brands that user can access in this store"""
    
    accessible_brands = Brand.objects.filter(
        brand_users__user=user,
        brand_users__can_login=True,
        brand_stores__store=store,
        brand_stores__is_active=True
    ).distinct()
    
    return accessible_brands
```

### Session Start

```python
def start_pos_session(user, terminal, selected_brand=None):
    """Start POS session with brand context"""
    
    # If terminal has fixed brand, use that
    terminal_brand = terminal.brand
    
    # Validate user has access
    validate_user_brand_access(user, terminal)
    
    # If user can access multiple brands, require selection
    if selected_brand:
        # Validate selected brand matches terminal
        if selected_brand != terminal_brand:
            raise ValidationError("Selected brand doesn't match terminal")
    
    # Create session
    session = StoreSession.objects.create(
        user=user,
        terminal=terminal,
        store=terminal.store,
        brand=terminal_brand,  # Session locked to brand
        opened_at=timezone.now()
    )
    
    return session
```

### Product Filtering

```python
def get_products_for_session(session):
    """Get products for current session's brand"""
    
    # Only show products for session's brand
    products = Product.objects.filter(
        brand=session.brand,
        is_active=True
    )
    
    return products
```

### Void/Discount Permission Check

```python
def can_void_bill(user, bill):
    """Check if user can void bill in this brand"""
    
    user_brand = UserBrand.objects.filter(
        user=user,
        brand=bill.brand
    ).first()
    
    if not user_brand:
        return False
    
    return user_brand.can_void or user_brand.is_manager

def can_apply_discount(user, brand):
    """Check if user can apply discount in this brand"""
    
    user_brand = UserBrand.objects.filter(
        user=user,
        brand=brand
    ).first()
    
    if not user_brand:
        return False
    
    return user_brand.can_discount or user_brand.is_manager
```

## 📊 Real-World Examples

### Example 1: Single Brand User

**User: Bob (SOTO LAMONGAN only)**
```python
# Bob's access
UserBrand:
  user=bob, brand=SOTO_LAMONGAN, can_login=True

# Bob tries to login at T01-SUMO (CHICKEN SUMO terminal)
validate_user_brand_access(bob, T01-SUMO)
# Result: PermissionDenied("You don't have access to CHICKEN SUMO")

# Bob logs in at T04-SOTO (SOTO LAMONGAN terminal)
validate_user_brand_access(bob, T04-SOTO)
# Result: Success! Bob can work here
```

### Example 2: Multi-Brand User

**User: Alice (CHICKEN SUMO + NASI PADANG)**
```python
# Alice's access
UserBrand:
  user=alice, brand=CHICKEN_SUMO, can_login=True
  user=alice, brand=NASI_PADANG, can_login=True

# Alice logs in at T01-SUMO (CHICKEN SUMO terminal)
validate_user_brand_access(alice, T01-SUMO)
# Result: Success! Alice can work here

# Alice logs in at T03-PADANG (NASI PADANG terminal)
validate_user_brand_access(alice, T03-PADANG)
# Result: Success! Alice can work here

# Alice tries T04-SOTO (SOTO LAMONGAN terminal)
validate_user_brand_access(alice, T04-SOTO)
# Result: PermissionDenied("You don't have access to SOTO LAMONGAN")
```

### Example 3: Manager (All Brands)

**User: Charlie (Manager, all brands)**
```python
# Charlie's access
UserBrand:
  user=charlie, brand=CHICKEN_SUMO, can_login=True, is_manager=True
  user=charlie, brand=NASI_PADANG, can_login=True, is_manager=True
  user=charlie, brand=SOTO_LAMONGAN, can_login=True, is_manager=True

# Charlie can login anywhere
validate_user_brand_access(charlie, T01-SUMO)  # ✓
validate_user_brand_access(charlie, T03-PADANG)  # ✓
validate_user_brand_access(charlie, T04-SOTO)  # ✓

# Charlie can void bills from any brand
can_void_bill(charlie, bill_from_sumo)  # ✓
can_void_bill(charlie, bill_from_padang)  # ✓
```

## 🔄 Session Management

### StoreSession Model Update

```python
class StoreSession(models.Model):
    user = models.ForeignKey(POSUser, on_delete=models.CASCADE)
    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)  # NEW!
    
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    
    opening_cash = models.DecimalField(max_digits=10, decimal_places=2)
    closing_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'brand', 'opened_at']),
        ]
```

### Bill Model Update

```python
class Bill(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)  # NEW!
    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE)
    session = models.ForeignKey(StoreSession, on_delete=models.CASCADE)
    
    # ... other fields
    
    class Meta:
        indexes = [
            models.Index(fields=['store', 'brand', 'created_at']),
        ]
```

## 📋 Migration Steps

### Step 1: Add User-Brand Relationship

```python
# Migration file
class Migration(migrations.Migration):
    operations = [
        # Add brands ManyToMany to POSUser
        migrations.AddField(
            model_name='posuser',
            name='brands',
            field=models.ManyToManyField(
                'Brand',
                through='UserBrand',
                related_name='users'
            ),
        ),
        
        # Create UserBrand model
        migrations.CreateModel(
            name='UserBrand',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4)),
                ('user', models.ForeignKey('POSUser', on_delete=models.CASCADE)),
                ('brand', models.ForeignKey('Brand', on_delete=models.CASCADE)),
                ('can_login', models.BooleanField(default=True)),
                ('can_void', models.BooleanField(default=False)),
                ('can_discount', models.BooleanField(default=False)),
                ('is_manager', models.BooleanField(default=False)),
            ],
        ),
        
        # Migrate existing users - give access to all brands
        migrations.RunPython(migrate_user_brands),
    ]

def migrate_user_brands(apps, schema_editor):
    """Give existing users access to all brands in their store"""
    POSUser = apps.get_model('core', 'POSUser')
    Brand = apps.get_model('core', 'Brand')
    UserBrand = apps.get_model('core', 'UserBrand')
    
    for user in POSUser.objects.all():
        # Get all brands in user's store
        store = user.store
        brands = Brand.objects.filter(brand_stores__store=store)
        
        for brand in brands:
            UserBrand.objects.create(
                user=user,
                brand=brand,
                can_login=True,
                can_void=(user.role == 'MANAGER'),
                can_discount=(user.role == 'MANAGER'),
                is_manager=(user.role == 'MANAGER')
            )
```

### Step 2: Add Brand to Session and Bill

```python
class Migration(migrations.Migration):
    operations = [
        # Add brand to StoreSession
        migrations.AddField(
            model_name='storesession',
            name='brand',
            field=models.ForeignKey('Brand', on_delete=models.CASCADE),
        ),
        
        # Add brand to Bill
        migrations.AddField(
            model_name='bill',
            name='brand',
            field=models.ForeignKey('Brand', on_delete=models.CASCADE),
        ),
        
        # Populate brand from terminal
        migrations.RunPython(populate_brand_from_terminal),
    ]

def populate_brand_from_terminal(apps, schema_editor):
    StoreSession = apps.get_model('core', 'StoreSession')
    Bill = apps.get_model('pos', 'Bill')
    
    # Update sessions
    for session in StoreSession.objects.all():
        session.brand = session.terminal.brand
        session.save()
    
    # Update bills
    for bill in Bill.objects.all():
        bill.brand = bill.terminal.brand
        bill.save()
```

## 🎯 Implementation Checklist

- [ ] Update POSUser model - add brands ManyToMany
- [ ] Create UserBrand model
- [ ] Add brand to StoreSession model
- [ ] Add brand to Bill model
- [ ] Update login validation - check UserBrand access
- [ ] Update brand selection UI (for multi-brand users)
- [ ] Update POS to filter by session brand
- [ ] Update void/discount permission checks
- [ ] Create user management UI with brand assignment
- [ ] Add brand column to reports
- [ ] Test single-brand user access
- [ ] Test multi-brand user access
- [ ] Test manager access to all brands

## ✅ Benefits

### 1. **Flexible User Assignment**
- User can work at 1 or multiple brands
- Manager can access all brands
- Cashier limited to specific brands

### 2. **Brand-Level Permissions**
- Void permission per brand
- Discount permission per brand
- Manager flag per brand

### 3. **Clear Access Control**
- User can only see products for their brand
- Can only process bills for their brand
- Clear audit trail

### 4. **Scalable**
- Add new brands → assign users
- Add new users → assign brands
- Flexible and maintainable

## 🎉 Conclusion

**User-Brand Assignment is Essential for Multi-Brand Stores!**

This architecture provides:
- ✅ Clear access control
- ✅ Flexible user assignment
- ✅ Brand-specific permissions
- ✅ Manager oversight
- ✅ Audit trail
- ✅ Scalability

**Implement UserBrand many-to-many for maximum flexibility!** 🚀

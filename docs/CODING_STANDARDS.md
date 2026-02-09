# 🎯 CODING STANDARDS & BEST PRACTICES
## FoodLife POS System - Frontend Development Guide

**Version:** 1.0  
**Last Updated:** February 10, 2026  
**Status:** ✅ Active Standard

---

## 📋 TABLE OF CONTENTS

1. [Technology Stack](#technology-stack)
2. [Architecture Principles](#architecture-principles)
3. [Component Patterns](#component-patterns)
4. [Do's and Don'ts](#dos-and-donts)
5. [Code Examples](#code-examples)
6. [File Structure](#file-structure)
7. [Testing Guidelines](#testing-guidelines)

---

## 🛠️ TECHNOLOGY STACK

### **Frontend Framework**
- **Primary:** Alpine.js 3.x (Reactive UI components)
- **Secondary:** HTMX 1.x (Server interactions)
- **Styling:** Tailwind CSS 3.x
- **Icons:** Heroicons (SVG inline)

### **When to Use What**

| Use Case | Technology | Reason |
|----------|-----------|--------|
| Forms with state | Alpine.js | Reactive, testable |
| Interactive UI (modals, tabs) | Alpine.js | Component-based |
| Server updates | HTMX | Simple, declarative |
| Static pages | HTML + Tailwind | No overhead |
| Simple clicks | Vanilla JS | Overkill for frameworks |

### **Dependencies (Local, Offline-First)**
```html
<!-- ✅ ALWAYS use local files -->
<link rel="stylesheet" href="{% static 'css/output.css' %}">
<script defer src="{% static 'js/alpine.min.js' %}"></script>
<script src="{% static 'js/htmx.min.js' %}"></script>

<!-- ❌ NEVER use CDN -->
<script src="https://cdn.jsdelivr.net/..."></script>
```

---

## 🏗️ ARCHITECTURE PRINCIPLES

### **1. Component-Based Architecture**

**✅ DO:** Create reusable Alpine.js components
```javascript
// Global component function
function modal() {
    return {
        show: false,
        type: 'info',
        title: '',
        message: '',
        
        showModal(options) {
            this.show = true;
            this.type = options.type || 'info';
            this.title = options.title;
            this.message = options.message;
        },
        
        closeModal() {
            this.show = false;
        }
    };
}
```

**❌ DON'T:** Scatter state across DOM elements
```javascript
// Bad: State in multiple places
const isOpen = document.getElementById('modal').style.display !== 'none';
const title = document.getElementById('modal-title').textContent;
```

---

### **2. Reactive State Management**

**✅ DO:** Use Alpine.js reactive data
```html
<div x-data="formHandler()">
    <select x-model="selectedCompany" @change="loadStores">
        <option value="">Select Company</option>
        <template x-for="company in companies" :key="company.id">
            <option :value="company.id" x-text="company.name"></option>
        </template>
    </select>
    
    <div x-show="selectedCompany" x-transition>
        <!-- Auto show/hide when company selected -->
    </div>
</div>
```

**❌ DON'T:** Manual DOM manipulation
```javascript
// Bad: Manual show/hide
companySelect.addEventListener('change', function() {
    if (this.value) {
        document.getElementById('store-container').style.display = 'block';
    } else {
        document.getElementById('store-container').style.display = 'none';
    }
});
```

---

### **3. Separation of Concerns**

**Structure:**
```
Component = Data + Methods + UI

- Data (state):       companies, selectedCompany, loading
- Methods (logic):    loadCompanies(), submitForm()
- UI (template):      x-model, x-show, @click bindings
```

**✅ DO:** Keep logic in component methods
```javascript
function setupStore() {
    return {
        // STATE
        companies: [],
        selectedCompany: '',
        loading: false,
        
        // LIFECYCLE
        init() {
            this.loadCompanies();
        },
        
        // METHODS
        async loadCompanies() {
            try {
                this.loading = true;
                const response = await fetch('/api/companies/');
                const data = await response.json();
                this.companies = data.companies;
            } catch (error) {
                this.handleError(error);
            } finally {
                this.loading = false;
            }
        },
        
        handleError(error) {
            console.error('Error:', error);
            this.showModal({
                type: 'error',
                title: 'Error',
                message: error.message
            });
        }
    };
}
```

**❌ DON'T:** Mix concerns
```javascript
// Bad: Business logic scattered everywhere
document.getElementById('submit').addEventListener('click', function() {
    const company = document.getElementById('company').value;
    if (!company) {
        alert('Select company'); // UI concern
        return;
    }
    
    fetch('/api/submit', { // API concern
        method: 'POST',
        body: JSON.stringify({ company })
    }).then(res => {
        if (res.ok) {
            window.location.href = '/success'; // Navigation concern
        }
    });
});
```

---

## 🎨 COMPONENT PATTERNS

### **Pattern 1: Form Handler**

```html
<div x-data="formHandler()">
    <form @submit.prevent="submitForm">
        <input type="text" x-model="formData.name" required>
        <button type="submit" :disabled="loading">
            <span x-show="!loading">Submit</span>
            <span x-show="loading">Processing...</span>
        </button>
    </form>
</div>

<script>
function formHandler() {
    return {
        formData: {
            name: '',
            email: ''
        },
        loading: false,
        errors: {},
        
        async submitForm() {
            if (!this.validate()) return;
            
            this.loading = true;
            try {
                const response = await fetch('/api/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify(this.formData)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.handleSuccess(data);
                } else {
                    this.handleError(data);
                }
            } catch (error) {
                this.handleError(error);
            } finally {
                this.loading = false;
            }
        },
        
        validate() {
            this.errors = {};
            
            if (!this.formData.name) {
                this.errors.name = 'Name is required';
            }
            
            return Object.keys(this.errors).length === 0;
        },
        
        getCsrfToken() {
            const cookie = document.cookie.split('; ')
                .find(row => row.startsWith('csrftoken='));
            return cookie ? cookie.split('=')[1] : '';
        }
    };
}
</script>
```

---

### **Pattern 2: Modal Component**

```html
<!-- Reusable modal component -->
<div x-show="modal.show" 
     x-transition
     class="fixed inset-0 z-50"
     style="display: none;">
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-black bg-opacity-50"></div>
    
    <!-- Modal -->
    <div class="flex items-center justify-center min-h-screen p-4">
        <div class="relative bg-white rounded-2xl shadow-2xl max-w-md w-full">
            <!-- Header -->
            <div class="px-6 py-5 border-b"
                 :class="{
                     'bg-green-50': modal.type === 'success',
                     'bg-red-50': modal.type === 'error',
                     'bg-yellow-50': modal.type === 'warning'
                 }">
                <h3 class="font-bold" x-text="modal.title"></h3>
            </div>
            
            <!-- Body -->
            <div class="px-6 py-5">
                <div x-html="modal.message"></div>
            </div>
            
            <!-- Footer -->
            <div class="px-6 py-4 bg-gray-50 flex justify-end space-x-3">
                <button @click="modal.show = false"
                        class="px-4 py-2 bg-gray-200 rounded">
                    Cancel
                </button>
                <button @click="modal.onConfirm()"
                        class="px-4 py-2 bg-blue-600 text-white rounded">
                    Confirm
                </button>
            </div>
        </div>
    </div>
</div>

<script>
function withModal() {
    return {
        modal: {
            show: false,
            type: 'info',
            title: '',
            message: '',
            onConfirm: () => { this.modal.show = false; }
        },
        
        showModal(options) {
            this.modal = {
                show: true,
                type: options.type || 'info',
                title: options.title || '',
                message: options.message || '',
                onConfirm: options.onConfirm || (() => { this.modal.show = false; })
            };
        }
    };
}
</script>
```

---

### **Pattern 3: List Management**

```html
<div x-data="listManager()">
    <!-- Search -->
    <input type="text" 
           x-model="search" 
           placeholder="Search..."
           class="w-full px-4 py-2 border rounded">
    
    <!-- List -->
    <div class="space-y-2 mt-4">
        <template x-for="item in filteredItems" :key="item.id">
            <div class="p-4 border rounded flex justify-between">
                <span x-text="item.name"></span>
                <button @click="removeItem(item.id)" 
                        class="text-red-600">
                    Delete
                </button>
            </div>
        </template>
        
        <div x-show="filteredItems.length === 0" class="text-gray-500 text-center p-4">
            No items found
        </div>
    </div>
</div>

<script>
function listManager() {
    return {
        items: [],
        search: '',
        
        get filteredItems() {
            if (!this.search) return this.items;
            
            return this.items.filter(item => 
                item.name.toLowerCase().includes(this.search.toLowerCase())
            );
        },
        
        init() {
            this.loadItems();
        },
        
        async loadItems() {
            const response = await fetch('/api/items/');
            const data = await response.json();
            this.items = data.items;
        },
        
        removeItem(id) {
            this.items = this.items.filter(item => item.id !== id);
        }
    };
}
</script>
```

---

## ✅ DO'S AND DON'TS

### **Alpine.js Usage**

| ✅ DO | ❌ DON'T |
|------|---------|
| Use for forms with multiple states | Use for simple button clicks |
| Use for interactive components | Use for static content |
| Create reusable component functions | Write inline x-data with 100+ lines |
| Use x-model for two-way binding | Use vanilla .value getters/setters |
| Use x-show/x-if for conditional rendering | Use style.display manually |
| Use @click, @submit.prevent | Use addEventListener |

### **API Calls**

| ✅ DO | ❌ DON'T |
|------|---------|
| Use async/await | Use nested .then() callbacks |
| Handle errors with try/catch | Ignore error cases |
| Show loading states | Leave users waiting without feedback |
| Use CSRF tokens | Skip security Headers |
| Centralize API calls in methods | Scatter fetch() calls everywhere |

```javascript
// ✅ GOOD: Centralized, clean
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ❌ BAD: Callback hell
fetch('/api/data')
    .then(res => res.json())
    .then(data => {
        fetch('/api/other')
            .then(res => res.json())
            .then(other => {
                // Nested mess...
            });
    });
```

### **UI Feedback**

| ✅ DO | ❌ DON'T |
|------|---------|
| Show loading spinners | Leave buttons clickable while processing |
| Disable buttons during submit | Allow double-submit |
| Show success/error modals | Use browser alert() |
| Use Tailwind transition classes | Use raw CSS animations |
| Provide clear error messages | Show generic "Error occurred" |

### **Code Organization**

| ✅ DO | ❌ DON'T |
|------|---------|
| One component = one responsibility | Create god objects |
| Extract reusable utilities | Copy-paste code |
| Comment complex logic | Over-comment obvious code |
| Use descriptive variable names | Use single letters (except i, j in loops) |
| Group related methods | Scatter methods randomly |

---

## 📁 FILE STRUCTURE

```
static/js/
├── components/          # Reusable Alpine.js components
│   ├── modal.js        # function modal() { ... }
│   ├── dropdown.js     # function dropdown() { ... }
│   ├── datepicker.js   # function datepicker() { ... }
│   └── form-wizard.js  # function formWizard() { ... }
│
├── utils/              # Utility functions
│   ├── api.js         # API call wrappers
│   ├── validators.js  # Form validation
│   ├── formatters.js  # Number/date formatting
│   └── helpers.js     # General helpers
│
├── pages/              # Page-specific logic (if complex)
│   ├── pos-main.js    # POS main page logic
│   └── setup.js       # Setup wizard logic
│
└── app.js              # Main initialization

templates/
├── base.html           # Global scripts loading
├── components/         # Reusable template partials
│   ├── modal.html
│   └── toast.html
└── pages/              # Page templates
    ├── pos/
    └── core/
```

---

## 🧪 TESTING GUIDELINES

### **Unit Tests for Alpine.js Components**

```javascript
// Example: Testing modal component
import { modal } from './components/modal.js';

describe('Modal Component', () => {
    test('opens modal with correct type', () => {
        const m = modal();
        
        m.showModal({
            type: 'success',
            title: 'Test',
            message: 'Hello'
        });
        
        expect(m.show).toBe(true);
        expect(m.type).toBe('success');
        expect(m.title).toBe('Test');
    });
    
    test('closes modal on confirmation', () => {
        const m = modal();
        m.show = true;
        
        m.closeModal();
        
        expect(m.show).toBe(false);
    });
});
```

---

## 📝 CODE REVIEW CHECKLIST

Before committing code, check:

- [ ] No external CDN dependencies (all local files)
- [ ] Alpine.js used for interactive components
- [ ] No manual DOM manipulation (unless absolutely necessary)
- [ ] Loading states shown during async operations
- [ ] Error handling implemented
- [ ] CSRF tokens included in API calls
- [ ] Tailwind classes used (no inline styles)
- [ ] Code is readable and well-structured
- [ ] No console.log left in production code
- [ ] Comments explain WHY, not WHAT

---

## 🚀 QUICK START FOR NEW FEATURES

### **Step 1: Choose Architecture**
```
Simple button click?  → Vanilla JS
Form with state?      → Alpine.js
Server interaction?   → HTMX
Both state + server?  → Alpine.js + HTMX
```

### **Step 2: Create Component**
```javascript
function myFeature() {
    return {
        // State
        data: [],
        loading: false,
        
        // Lifecycle
        init() {
            this.loadData();
        },
        
        // Methods
        async loadData() { ... },
        handleSubmit() { ... }
    };
}
```

### **Step 3: Bind to Template**
```html
<div x-data="myFeature()">
    <!-- Use x-model, x-show, @click -->
</div>
```

---

## 📚 ADDITIONAL RESOURCES

- **Alpine.js Docs:** https://alpinejs.dev/
- **HTMX Docs:** https://htmx.org/
- **Tailwind CSS:** https://tailwindcss.com/
- **Project Patterns:** See `templates/core/setup_store.html` for reference implementation

---

## 🔄 MIGRATION GUIDE

### **Converting Vanilla JS to Alpine.js**

**Before (Vanilla JS):**
```javascript
document.addEventListener('DOMContentLoaded', function() {
    const select = document.getElementById('company');
    const container = document.getElementById('store-container');
    
    select.addEventListener('change', function() {
        if (this.value) {
            container.style.display = 'block';
        }
    });
});
```

**After (Alpine.js):**
```html
<div x-data="{ company: '' }">
    <select x-model="company">
        <option value="">Select</option>
    </select>
    
    <div x-show="company" x-transition>
        <!-- Auto show/hide -->
    </div>
</div>
```

---

## ⚖️ DECISION MATRIX

When in doubt, use this matrix:

| Requirement | Solution |
|-------------|----------|
| Need reactivity | Alpine.js ✅ |
| Need server updates | HTMX ✅ |
| Need both | Alpine.js + HTMX ✅ |
| Static page | HTML + Tailwind ✅ |
| Single action | Vanilla JS ✅ |
| Complex state | Alpine.js ✅ |
| Real-time updates | WebSocket + Alpine.js ✅ |

---

## 🎓 LEARNING PATH

1. **Week 1:** Learn Alpine.js basics (x-data, x-model, x-show, x-if)
2. **Week 2:** Learn Alpine.js methods (@click, @submit, lifecycle hooks)
3. **Week 3:** Learn HTMX basics (hx-get, hx-post, hx-trigger)
4. **Week 4:** Combine Alpine.js + HTMX for powerful interactions

---

## 📞 SUPPORT

- **Questions:** Review this document first
- **Examples:** Check `templates/core/setup_store.html`
- **New Patterns:** Discuss with team before implementing

---

**Last Updated:** February 10, 2026  
**Maintained By:** Development Team  
**Version:** 1.0

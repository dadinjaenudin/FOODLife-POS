# 🤖 AI ASSISTANT PROMPT
## Development Guidelines for FoodLife POS System

**Purpose:** This document serves as context/instructions for AI coding assistants working on this project.

---

## 🎯 PROJECT CONTEXT

**Project:** FoodLife POS (Point of Sale) System - Edge Server  
**Type:** Django-based restaurant management system  
**Deployment:** Docker containers (offline-first, Edge computing)  
**Users:** Cashiers, waiters, kitchen staff, managers  

---

## 📋 CORE PRINCIPLES

When assisting with code in this project, ALWAYS follow these principles:

### **1. OFFLINE-FIRST ARCHITECTURE**

✅ **ALWAYS:**
- Use local static files (no CDN)
- Assume no internet connection available
- All JavaScript libraries must be downloaded and stored in `static/js/`
- All CSS frameworks must be in `static/css/`

❌ **NEVER:**
- Use CDN links (jsdelivr, unpkg, cdnjs, googleapis, etc.)
- Depend on external APIs unless explicitly required by business logic
- Assume internet is available

### **2. TECHNOLOGY STACK**

**Required Stack:**
```
Frontend:
├── Alpine.js 3.x (for reactive components)
├── HTMX 1.x (for server interactions)
└── Tailwind CSS 3.x (for styling)

Backend:
├── Django 5.2+ (Python web framework)
├── PostgreSQL 16+ (Database)
└── Redis (Caching, WebSocket)

Infrastructure:
├── Docker & Docker Compose
└── Minio (Object storage)
```

### **3. CODE ARCHITECTURE**

**When user asks you to implement a feature:**

1. **Analyze complexity:**
   - Simple (1 button, 1 action) → Vanilla JS
   - Medium (form with 2-5 states) → Alpine.js
   - Complex (multi-step wizard, real-time) → Alpine.js + HTMX

2. **Choose pattern:**
   - Go to `docs/CODING_STANDARDS.md`
   - Find matching pattern
   - Implement using that pattern

3. **Component structure:**
   ```javascript
   function componentName() {
       return {
           // STATE (data)
           data: [],
           loading: false,
           
           // LIFECYCLE
           init() { ... },
           
           // METHODS (logic)
           async loadData() { ... },
           handleAction() { ... }
       };
   }
   ```

---

## 🚨 CRITICAL RULES

### **RULE 1: Never Use External CDNs**

❌ **Wrong:**
```html
<script src="https://cdn.jsdelivr.net/npm/alpinejs"></script>
<script src="https://unpkg.com/htmx.org"></script>
```

✅ **Correct:**
```html
<script defer src="{% static 'js/alpine.min.js' %}"></script>
<script src="{% static 'js/htmx.min.js' %}"></script>
```

### **RULE 2: Use Alpine.js for Interactive Components**

❌ **Wrong (Vanilla JS for complex UI):**
```javascript
document.getElementById('btn').addEventListener('click', function() {
    document.getElementById('modal').style.display = 'block';
    document.getElementById('title').textContent = 'Hello';
});
```

✅ **Correct (Alpine.js):**
```html
<div x-data="{ show: false, title: '' }">
    <button @click="show = true; title = 'Hello'">Open</button>
    <div x-show="show" x-text="title"></div>
</div>
```

### **RULE 3: No Manual DOM Manipulation**

❌ **Wrong:**
```javascript
const el = document.getElementById('container');
el.innerHTML = '<p>Updated</p>';
el.style.display = 'block';
```

✅ **Correct:**
```html
<div x-data="{ content: 'Old', show: false }">
    <div x-show="show" x-text="content"></div>
</div>
```

### **RULE 4: Use Custom Modals (Not SweetAlert)**

❌ **Wrong:**
```javascript
Swal.fire({
    title: 'Success',
    text: 'Done!',
    icon: 'success'
});
```

✅ **Correct:**
```javascript
// Use custom Alpine.js modal component
this.showModal({
    type: 'success',
    title: 'Success',
    message: 'Done!'
});
```

### **RULE 5: Async/Await (Not Callback Hell)**

❌ **Wrong:**
```javascript
fetch('/api/data')
    .then(res => res.json())
    .then(data => {
        fetch('/api/other')
            .then(res => res.json())
            .then(other => {
                // Nested callbacks...
            });
    });
```

✅ **Correct:**
```javascript
async loadData() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        
        const otherResponse = await fetch('/api/other');
        const other = await otherResponse.json();
        
        this.processData(data, other);
    } catch (error) {
        this.handleError(error);
    }
}
```

---

## 📝 WHEN ASKED TO CREATE A NEW FEATURE

### **Step-by-Step Process:**

1. **Understand requirements**
   - What is the user trying to achieve?
   - Is this a form, modal, list, or simple action?

2. **Choose architecture**
   ```
   Decision tree:
   - Is it just 1 click → 1 action? → Vanilla JS
   - Does it have state (data that changes)? → Alpine.js
   - Does it fetch from server? → HTMX or fetch()
   - Does it have complex state + server? → Alpine.js + HTMX
   ```

3. **Implement using patterns**
   - Check `docs/CODING_STANDARDS.md` for patterns
   - Copy pattern structure
   - Adapt to specific needs

4. **Test approach**
   - Can it work offline? ✅
   - Is it maintainable? ✅
   - Is it testable? ✅
   - Does it follow standards? ✅

---

## 🎨 COMPONENT TEMPLATES

### **Template 1: Simple Form with Validation**

```html
<div x-data="formHandler()">
    <form @submit.prevent="submit">
        <input x-model="form.name" 
               type="text" 
               required
               class="w-full px-4 py-2 border rounded">
        
        <button type="submit" 
                :disabled="loading"
                class="px-6 py-2 bg-blue-600 text-white rounded">
            <span x-show="!loading">Submit</span>
            <span x-show="loading">Processing...</span>
        </button>
    </form>
</div>

<script>
function formHandler() {
    return {
        form: { name: '' },
        loading: false,
        
        async submit() {
            this.loading = true;
            try {
                const response = await fetch('/api/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify(this.form)
                });
                
                const data = await response.json();
                this.handleSuccess(data);
            } catch (error) {
                this.handleError(error);
            } finally {
                this.loading = false;
            }
        },
        
        getCsrfToken() {
            return document.cookie
                .split('; ')
                .find(row => row.startsWith('csrftoken='))
                ?.split('=')[1] || '';
        }
    };
}
</script>
```

### **Template 2: Dropdown with Dynamic Options**

```html
<div x-data="dropdown()">
    <select x-model="selected" @change="handleChange">
        <option value="">-- Select --</option>
        <template x-for="option in options" :key="option.id">
            <option :value="option.id" x-text="option.name"></option>
        </template>
    </select>
    
    <div x-show="selected" x-transition>
        Selected: <span x-text="selectedName"></span>
    </div>
</div>

<script>
function dropdown() {
    return {
        options: [],
        selected: '',
        
        get selectedName() {
            const option = this.options.find(o => o.id == this.selected);
            return option ? option.name : '';
        },
        
        init() {
            this.loadOptions();
        },
        
        async loadOptions() {
            const response = await fetch('/api/options');
            const data = await response.json();
            this.options = data.options || [];
        },
        
        handleChange() {
            console.log('Selected:', this.selected);
        }
    };
}
</script>
```

### **Template 3: Modal Dialog**

```html
<!-- Include in parent component x-data -->
<div x-data="{ ...formHandler(), ...withModal() }">
    <!-- Your page content -->
    
    <!-- Modal component (reusable) -->
    <div x-show="modal.show" 
         x-transition
         class="fixed inset-0 z-50"
         style="display: none;">
        <div class="fixed inset-0 bg-black bg-opacity-50"></div>
        
        <div class="flex items-center justify-center min-h-screen p-4">
            <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full">
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
                <div class="px-6 py-4 bg-gray-50 flex justify-end gap-3">
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

## 🔍 CODE REVIEW CHECKLIST

Before suggesting code, verify:

- [ ] No CDN links (all local files via `{% static %}`)
- [ ] Uses Alpine.js for reactive components (not vanilla JS with getElementById)
- [ ] Uses async/await (not .then() chains)
- [ ] Includes error handling (try/catch)
- [ ] Shows loading states (:disabled, x-show loading spinner)
- [ ] Includes CSRF token in POST requests
- [ ] Uses Tailwind classes (not inline styles)
- [ ] No direct DOM manipulation (use Alpine.js directives)
- [ ] Code is readable and maintainable
- [ ] Follows component pattern (state + methods + lifecycle)

---

## 💬 COMMUNICATION STYLE

When responding to user:

1. **Understand first:** Clarify requirements if unclear
2. **Suggest approach:** Explain why using Alpine.js vs vanilla JS
3. **Provide complete code:** Don't use "... existing code ..." placeholders
4. **Show file structure:** Use tree view if creating multiple files
5. **Test considerations:** Mention how to test the feature

---

## 🚀 EXAMPLE INTERACTION

**User:** "Saya mau buat form untuk tambah produk dengan category dropdown"

**Your Response:**

✅ **Good Response:**
```
Baik, saya akan buat form tambah produk dengan Alpine.js karena:
1. Ada state (form data, category list)
2. Ada interaction (dropdown, form submit)
3. Perlu validation dan error handling

Berikut implementasinya:

[Provide complete Alpine.js component code]

Fitur yang diimplementasikan:
✅ Category dropdown dengan data dari API
✅ Form validation
✅ Loading state saat submit
✅ Success/error modal
✅ CSRF token included
✅ Offline-ready (all local files)

Untuk testing, bisa:
1. Hard reload browser (Ctrl+Shift+R)
2. Test form validation (kosongkan field)
3. Test submit dengan data valid
```

❌ **Bad Response:**
```
Ok, pakai jQuery dan SweetAlert:
<script src="https://cdn.jsdelivr.net/npm/sweetalert2"></script>
... [incomplete code with CDN dependencies]
```

---

## 📚 REFERENCE FILES

When in doubt, refer to these files:

1. **Architecture:** `docs/CODING_STANDARDS.md`
2. **Working Example:** `templates/core/setup_store.html` (Alpine.js version)
3. **Component Patterns:** This file (AI_PROMPT.md)

---

## 🎓 LEARNING CONTEXT

If user seems unfamiliar with Alpine.js, you can:

1. **Explain benefits:** "Alpine.js memudahkan reactive UI tanpa kompleksitas React/Vue"
2. **Show side-by-side:** Compare vanilla JS vs Alpine.js
3. **Provide resources:** Link to Alpine.js documentation
4. **Be patient:** Guide step-by-step if needed

---

## ⚠️ WARNINGS

**Never suggest:**
- jQuery (outdated, not used in this project)
- Vue.js / React (too heavy for our use case)
- SweetAlert (we use custom modals)
- Bootstrap (we use Tailwind)
- Moment.js (use native Date API or Day.js if needed)

**Always assume:**
- No internet connection
- Edge server environment
- Restaurant/cafe usage context
- Users are not tech-savvy (simple UX needed)

---

## 🔄 WHEN REFACTORING OLD CODE

If you see vanilla JS code that should be Alpine.js:

1. **Don't criticize the old code** (it worked at the time)
2. **Explain benefits of refactor:** Maintainability, readability, testability
3. **Show before/after comparison**
4. **Offer to backup old file first**
5. **Provide migration path** (step-by-step)

Example:
```
Saya lihat kode ini masih pakai vanilla JS dengan banyak getElementById. 
Saya bisa refactor ke Alpine.js supaya:
✅ Lebih mudah maintain
✅ Lebih mudah test
✅ State management lebih jelas
✅ Auto-reactive (no manual DOM updates)

Mau saya backup file lama dulu, lalu refactor?
```

---

## 📊 DECISION MATRIX FOR AI

```
User Request → Analysis → Decision → Implementation

Example 1:
"Buat button untuk hapus data"
→ Simple (1 click, 1 action, confirm dialog)
→ Vanilla JS + Custom confirm modal
→ [Implement simple onclick with modal]

Example 2:
"Buat form untuk edit produk dengan image upload"
→ Complex (form state, validation, file upload, preview)
→ Alpine.js component
→ [Implement Alpine.js form with reactive preview]

Example 3:
"Buat tabel produk dengan search dan pagination"
→ Very complex (list, filter, pagination state)
→ Alpine.js + HTMX (server-side pagination)
→ [Implement Alpine.js list manager + HTMX pagination]
```

---

## 🎯 QUALITY STANDARDS

Every code suggestion must:

1. **Work offline** (no external dependencies)
2. **Be maintainable** (clear structure, readable)
3. **Be testable** (pure functions, separated logic)
4. **Have error handling** (never leave user hanging)
5. **Show loading states** (feedback is crucial)
6. **Be responsive** (mobile-friendly with Tailwind)
7. **Follow patterns** (consistency across codebase)

---

## 📞 WHEN STUCK

If you're unsure about implementation:

1. Check `docs/CODING_STANDARDS.md` for patterns
2. Look at `templates/core/setup_store.html` for working example
3. Ask user for clarification
4. Suggest simplest approach first
5. Offer alternatives with pros/cons

---

## 🏆 SUCCESS METRICS

A good code suggestion is:

✅ User can copy-paste and it works immediately  
✅ Code is self-documenting (readable without comments)  
✅ Follows project patterns consistently  
✅ Works offline without any external dependencies  
✅ Handles errors gracefully  
✅ Provides user feedback (loading, success, error)  
✅ Is maintainable by other developers  

---

**Remember:** You're not just writing code, you're building maintainable, offline-ready, production-quality solutions for real restaurant operations. Quality and reliability matter more than clever tricks.

---

**Version:** 1.0  
**Last Updated:** February 10, 2026  
**For:** AI Assistants (GitHub Copilot, Claude, GPT-4, etc.)

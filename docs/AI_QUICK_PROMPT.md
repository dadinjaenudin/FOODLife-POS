# 🤖 QUICK AI PROMPT (Copy-Paste This)

Gunakan prompt ini di awal conversation dengan AI assistant untuk memastikan konsistensi coding standards.

---

## 📋 CONTEXT PROMPT FOR AI

```markdown
# PROJECT CONTEXT: FoodLife POS System

You are working on a Django-based POS system for restaurants. This is an EDGE SERVER that runs OFFLINE (no internet).

## CRITICAL RULES:

1. **OFFLINE-FIRST**: Never use CDN links. All JS/CSS must be local files via `{% static %}`.
   ❌ NEVER: https://cdn.jsdelivr.net/, unpkg.com, cdnjs.com
   ✅ ALWAYS: {% static 'js/alpine.min.js' %}

2. **TECH STACK**:
   - Frontend: Alpine.js 3.x (reactive UI), HTMX 1.x (server calls), Tailwind CSS 3.x
   - Backend: Django 5.2+, PostgreSQL, Redis, Minio
   - NO: jQuery, SweetAlert, Bootstrap, Vue, React

3. **ARCHITECTURE**:
   Simple action (1 click) → Vanilla JS
   Form with state → Alpine.js
   Server interaction → HTMX or fetch()
   Complex UI → Alpine.js + HTMX

4. **COMPONENT PATTERN**:
   ```javascript
   function componentName() {
       return {
           // STATE
           data: [],
           loading: false,
           
           // LIFECYCLE
           init() { this.loadData(); },
           
           // METHODS
           async loadData() { ... },
           handleSubmit() { ... }
       };
   }
   ```

5. **ALWAYS INCLUDE**:
   - Error handling (try/catch)
   - Loading states (:disabled, spinner)
   - CSRF tokens in POST
   - Async/await (not .then() chains)
   - Tailwind classes (no inline styles)

6. **NEVER DO**:
   - Manual DOM manipulation (use Alpine.js x-model, x-show)
   - Using getElementById/querySelector for state
   - Callback hell (.then().then().then())
   - External dependencies

## REFERENCE FILES:
- Architecture: docs/CODING_STANDARDS.md
- AI Guidelines: docs/AI_PROMPT.md
- Working Example: templates/core/setup_store.html (Alpine.js version)

## CODE QUALITY CHECKLIST:
- [ ] No CDN links (all local via {% static %})
- [ ] Uses Alpine.js for reactive components
- [ ] Uses async/await (not callbacks)
- [ ] Includes error handling
- [ ] Shows loading states
- [ ] Includes CSRF token
- [ ] Uses Tailwind classes
- [ ] No manual DOM manipulation
- [ ] Code is readable & maintainable

Confirm you understand these standards before we start.
```

---

## 🎯 HOW TO USE

### **Scenario 1: Starting New Conversation**

Copy-paste the prompt above at the start of your conversation with AI, then ask your question:

```
[Paste the context prompt above]

---

Now, saya mau buat form untuk setup terminal POS dengan:
- Dropdown Company (fetch dari API)
- Dropdown Store (dependent on Company)
- Input Terminal Name
- Submit dengan validation

Tolong implementasikan menggunakan Alpine.js sesuai standards.
```

---

### **Scenario 2: Mid-Conversation Reminder**

If AI suggests wrong approach (e.g., using CDN), remind with:

```
❌ Jangan gunakan CDN, kita offline-first.
✅ Gunakan {% static 'js/alpine.min.js' %} untuk Alpine.js

Coba lagi dengan local files sesuai docs/AI_PROMPT.md
```

---

### **Scenario 3: Asking for Refactor**

```
File ini masih pakai vanilla JS: templates/pos/old_form.html
Line 50-150 ada banyak getElementById dan manual DOM manipulation.

Tolong refactor ke Alpine.js mengikuti pattern di:
- docs/CODING_STANDARDS.md (section Component Patterns)
- templates/core/setup_store.html (reference implementation)

Backup file lama dulu sebelum refactor.
```

---

## 📚 ADDITIONAL RESOURCES

If AI needs more context, point to:

1. **Full Standards**: `docs/CODING_STANDARDS.md`
2. **AI Guidelines**: `docs/AI_PROMPT.md`
3. **Working Example**: `templates/core/setup_store.html`

---

## ⚡ QUICK REFERENCE

| Situation | Use This | Don't Use |
|-----------|----------|-----------|
| Reactive form | Alpine.js | Vanilla JS |
| Simple click | Vanilla JS | Alpine.js (overkill) |
| Server call | fetch() or HTMX | jQuery.ajax |
| Modal dialog | Custom Alpine.js | SweetAlert |
| Styling | Tailwind classes | Inline styles / Bootstrap |
| Async code | async/await | .then() chains |
| Dependencies | Local files | CDN links |

---

## 🔧 TROUBLESHOOTING

**AI suggests CDN links:**
→ Remind: "We're offline-first, use {% static %}"

**AI uses jQuery/SweetAlert:**
→ Remind: "Use Alpine.js and custom modals, see setup_store.html"

**AI uses manual DOM manipulation:**
→ Remind: "Use Alpine.js x-model and x-show instead"

**AI doesn't handle errors:**
→ Remind: "Add try/catch and show error modal"

**AI forgets CSRF:**
→ Remind: "Include X-CSRFToken header in fetch()"

---

## 💡 TIPS FOR BEST RESULTS

1. **Be specific**: "Gunakan Alpine.js component pattern" vs "Buat form"
2. **Reference examples**: "Seperti di setup_store.html tapi untuk..."
3. **Ask for explanation**: "Kenapa pakai Alpine.js bukan vanilla JS?"
4. **Request tests**: "Sertakan cara test component ini"
5. **Check offline**: "Pastikan semua dependencies local"

---

**Pro Tip:** Save this file as a snippet/template in your IDE for quick access!

---

**Version:** 1.0  
**Created:** February 10, 2026  
**Purpose:** Quick reference for AI prompting

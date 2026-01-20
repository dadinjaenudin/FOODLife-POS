# UI Design Template & Guidelines
**POS Django HTMX - Compact & Clean Design System**

---

## 📋 Design Principles

### 1. **Compact Layout Philosophy**
- Minimize padding to show more data in viewport
- Use small font sizes but maintain readability
- Reduce spacing between elements
- Optimize for data-dense views

### 2. **Responsive & Clean**
- Mobile-first approach
- Clean visual hierarchy
- Consistent spacing scale
- Professional color palette

---

## 🎨 Spacing & Sizing Scale

### Container Spacing
```html
<!-- Main Container (Ultra-Compact for List Pages) -->
<div class="container mx-auto px-4 py-1.5">  <!-- Ultra-compact: px-4 py-1.5 -->
  
<!-- Section Spacing -->
<div class="mb-1.5">  <!-- Between sections: mb-1.5 -->
<div class="mb-2">    <!-- Slightly more: mb-2 -->
<div class="gap-1.5"> <!-- Grid/Flex gap: gap-1.5 -->
<div class="gap-2">   <!-- Medium gap: gap-2 -->
```

### Card/Panel Padding
```html
<!-- Main Cards/Filters -->
<div class="bg-white rounded-lg shadow p-2.5">  <!-- Standard: p-2.5 -->

<!-- Stat Cards -->
<div class="bg-white rounded-lg shadow p-1.5">  <!-- Ultra-compact: p-1.5 -->

<!-- Small Cards/Badges -->
<div class="px-2 py-1">     <!-- Minimal: px-2 py-1 -->
<div class="px-1.5 py-0.5"> <!-- Tiny: px-1.5 py-0.5 -->
```

---

## 📝 Typography Scale

### Headers
```html
<!-- Page Title (Ultra-Compact) -->
<h1 class="text-xl font-bold text-gray-800">Products Management</h1>
<p class="text-xs text-gray-600">Subtitle text</p>

<!-- Section Title -->
<h2 class="text-lg font-semibold text-gray-800 mb-2">Section Title</h2>
<h3 class="text-base font-semibold text-gray-900">Subsection</h3>
```

### Body Text
```html
<!-- Standard Text -->
<div class="text-xs text-gray-700">Normal text</div>

<!-- Compact Text (for tables) -->
<div class="text-xs text-gray-700">Table cell text</div>

<!-- Labels -->
<label class="block text-xs font-medium text-gray-700 mb-0.5">Field Label</label>

<!-- Help Text -->
<p class="text-xs text-gray-500 mt-0.5">Helper text</p>
```

---

## 📊 Table Design (Compact)

### Table Structure
```html
<div class="bg-white rounded-lg shadow overflow-hidden">
  <div class="overflow-x-auto">
    <table class="min-w-full divide-y divide-gray-200">
      <!-- Compact Header -->
      <thead class="bg-gray-50">
        <tr>
          <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            Column Name
          </th>
        </tr>
      </thead>
      
      <!-- Compact Body -->
      <tbody class="bg-white divide-y divide-gray-200">
        <tr class="hover:bg-gray-50">
          <td class="px-3 py-2 whitespace-nowrap">
            <div class="text-xs text-gray-900">Cell content</div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
```

### Table Cell Patterns

**With Image:**
```html
<td class="px-3 py-2 whitespace-nowrap">
  <div class="flex items-center">
    <img src="..." class="h-8 w-8 rounded object-cover mr-2">
    <div class="text-xs font-medium text-gray-900">Product Name</div>
  </div>
</td>
```

**Numeric (Right-aligned):**
```html
<td class="px-3 py-2 whitespace-nowrap text-right">
  <div class="text-xs font-semibold text-gray-900">Rp 25,000</div>
  <div class="text-xs text-gray-500">Cost: 15,000</div>
</td>
```

**Badge/Status:**
```html
<td class="px-3 py-2 whitespace-nowrap text-center">
  <span class="px-1.5 py-0.5 bg-green-100 text-green-700 text-xs font-semibold rounded">
    Active
  </span>
</td>
```

**Empty State:**
```html
<td class="px-3 py-2 whitespace-nowrap">
  <span class="text-xs text-gray-400">-</span>
</td>
```

---

## 🔘 Buttons & Actions

### Primary Buttons
```html
<!-- Standard Button -->
<button class="px-3 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition">
  Button Text
</button>

<!-- Icon Button (Compact) -->
<button class="inline-flex items-center px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition">
  <svg class="w-3 h-3">...</svg>
</button>

<!-- Icon Only (Minimal) -->
<button class="p-1.5 bg-blue-600 text-white rounded hover:bg-blue-700" title="Tooltip">
  <svg class="w-3 h-3">...</svg>
</button>
```

### Button Variants
```html
<!-- Primary -->
<button class="bg-blue-600 hover:bg-blue-700 text-white">Primary</button>

<!-- Success -->
<button class="bg-green-600 hover:bg-green-700 text-white">Success</button>

<!-- Danger -->
<button class="bg-red-600 hover:bg-red-700 text-white">Danger</button>

<!-- Secondary -->
<button class="bg-gray-100 hover:bg-gray-200 text-gray-700">Secondary</button>

<!-- Warning -->
<button class="bg-orange-600 hover:bg-orange-700 text-white">Warning</button>
```

### Action Button Group
```html
<div class="flex items-center justify-center gap-1">
  <a href="#" class="inline-flex items-center px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700" title="View">
    <svg class="w-3 h-3">👁️</svg>
  </a>
  <a href="#" class="inline-flex items-center px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700" title="Edit">
    <svg class="w-3 h-3">✏️</svg>
  </a>
  <a href="#" class="inline-flex items-center px-2 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700" title="Delete">
    <svg class="w-3 h-3">🗑️</svg>
  </a>
</div>
```

---

## 📋 Form Elements

### Input Fields (Ultra-Compact)
```html
<!-- Standard Input -->
<div>
  <label class="block text-xs font-medium text-gray-700 mb-0.5">Field Label</label>
  <input type="text" 
         class="w-full px-2.5 py-1.5 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
         placeholder="Enter value">
  <p class="mt-0.5 text-xs text-gray-500">Helper text</p>
</div>

<!-- Select -->
<select class="w-full px-2.5 py-1.5 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
  <option>Option 1</option>
</select>

<!-- Textarea -->
<textarea rows="3" 
          class="w-full px-2.5 py-1.5 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
</textarea>

<!-- Checkbox -->
<label class="flex items-center">
  <input type="checkbox" class="w-4 h-4 text-blue-600 rounded">
  <span class="ml-2 text-xs text-gray-700">Checkbox label</span>
</label>
```

### Form Layout
```html
<!-- Grid Layout (Ultra-Compact) -->
<form class="grid grid-cols-1 md:grid-cols-4 gap-2">
  <div><!-- Field 1 --></div>
  <div><!-- Field 2 --></div>
  <div class="col-span-2"><!-- Full width field --></div>
</form>

<!-- Inline Form -->
<form class="flex items-end gap-2">
  <div class="flex-1"><!-- Input --></div>
  <button><!-- Submit --></button>
</form>
```

---

## 🏷️ Badges & Tags

### Status Badges
```html
<!-- Active/Success -->
<span class="px-1.5 py-0.5 bg-green-100 text-green-700 text-xs font-semibold rounded">
  Active
</span>

<!-- Inactive/Error -->
<span class="px-1.5 py-0.5 bg-red-100 text-red-700 text-xs font-semibold rounded">
  Inactive
</span>

<!-- Warning -->
<span class="px-1.5 py-0.5 bg-orange-100 text-orange-700 text-xs font-semibold rounded">
  Pending
</span>

<!-- Info -->
<span class="px-1.5 py-0.5 bg-blue-100 text-blue-700 text-xs font-semibold rounded">
  Processing
</span>

<!-- Neutral -->
<span class="px-1.5 py-0.5 bg-gray-100 text-gray-700 text-xs font-semibold rounded">
  Draft
</span>
```

### Category Tags
```html
<div class="inline-block bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded text-xs">
  Category Name
</div>
```

### Count Badge
```html
<span class="ml-0.5 px-1 py-0.5 bg-purple-800 text-white text-xs rounded-full">
  5
</span>
```

---

## 📈 Stats Cards

### Ultra-Compact Stat Card
```html
<div class="bg-white rounded-lg shadow p-1.5">
  <div class="text-lg font-bold text-gray-800">125</div>
  <div class="text-xs text-gray-600">Total Items</div>
</div>

<!-- With Color Background -->
<div class="bg-green-50 rounded-lg shadow p-1.5">
  <div class="text-lg font-bold text-green-700">95</div>
  <div class="text-xs text-gray-600">Active</div>
</div>
```

### Stats Grid (Ultra-Compact)
```html
<div class="grid grid-cols-1 md:grid-cols-4 gap-1.5 mb-1.5">
  <div class="bg-white rounded-lg shadow p-1.5">
    <div class="text-lg font-bold text-gray-800">{{ total }}</div>
    <div class="text-xs text-gray-600">Total</div>
  </div>
  <!-- More stats... -->
</div>
```

---

## 📄 Pagination (Ultra-Compact)

```html
<div class="bg-white rounded-lg shadow mt-2 px-3 py-2">
  <div class="flex items-center justify-between">
    <!-- Info Text -->
    <div class="text-xs text-gray-700">
      Showing <span class="font-semibold">1</span> to 
      <span class="font-semibold">20</span> of 
      <span class="font-semibold">100</span> items
    </div>
    
    <!-- Page Numbers -->
    <div class="flex items-center gap-1">
      <a href="?page=1" class="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded">
        ««
      </a>
      <a href="?page=1" class="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded">
        ‹
      </a>
      <span class="px-2 py-1 text-xs bg-blue-600 text-white rounded font-semibold">
        1
      </span>
      <a href="?page=2" class="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded">
        2
      </a>
      <a href="?page=2" class="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded">
        ›
      </a>
      <a href="?page=5" class="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded">
        »»
      </a>
    </div>
  </div>
</div>
```

---

## 🎨 Color Palette

### Semantic Colors
```
- Primary (Blue):   bg-blue-600, text-blue-700, border-blue-200
- Success (Green):  bg-green-600, text-green-700, border-green-200
- Danger (Red):     bg-red-600, text-red-700, border-red-200
- Warning (Orange): bg-orange-600, text-orange-700, border-orange-200
- Info (Blue):      bg-blue-600, text-blue-700, border-blue-200
- Neutral (Gray):   bg-gray-600, text-gray-700, border-gray-200
```

### Background Colors
```
- Light Backgrounds:
  bg-gray-50   (Table headers, subtle backgrounds)
  bg-blue-50   (Info boxes)
  bg-green-50  (Success boxes)
  bg-red-50    (Error boxes)

- Badge Backgrounds:
  bg-green-100 (Success badges)
  bg-red-100   (Error badges)
  bg-orange-100 (Warning badges)
  bg-purple-100 (Category badges)
```

---

## 📦 Modal Design

### Modal Container
```html
<div id="modal" class="hidden fixed inset-0 bg-gray-900 bg-opacity-50 z-50">
  <div class="flex items-center justify-center min-h-screen p-4">
    <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full">
      <!-- Header -->
      <div class="bg-gradient-to-r from-blue-500 to-blue-600 p-4 rounded-t-2xl">
        <h3 class="text-lg font-bold text-white">Modal Title</h3>
      </div>
      
      <!-- Body -->
      <div class="p-4">
        <p class="text-sm text-gray-700">Modal content here</p>
      </div>
      
      <!-- Footer -->
      <div class="flex justify-end gap-2 p-4 border-t">
        <button class="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg">
          Cancel
        </button>
        <button class="px-3 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg">
          Confirm
        </button>
      </div>
    </div>
  </div>
</div>
```

---

## 🔔 Alert/Notification Boxes

### Info Box
```html
<div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
  <p class="text-xs text-blue-800">
    <strong>ℹ️ Info:</strong> Information message here
  </p>
</div>
```

### Warning Box
```html
<div class="bg-orange-50 border border-orange-200 rounded-lg p-3">
  <p class="text-xs text-orange-800">
    <strong>⚠️ Warning:</strong> Warning message here
  </p>
</div>
```

### Success Box
```html
<div class="bg-green-50 border border-green-200 rounded-lg p-3">
  <p class="text-xs text-green-800">
    <strong>✅ Success:</strong> Success message here
  </p>
</div>
```

### Error Box
```html
<div class="bg-red-50 border border-red-200 rounded-lg p-3">
  <p class="text-xs text-red-800">
    <strong>❌ Error:</strong> Error message here
  </p>
</div>
```

---

## 📱 Responsive Design

### Mobile-First Breakpoints
```html
<!-- Stack on mobile, grid on desktop -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
  <!-- Cards -->
</div>

<!-- Hide on mobile -->
<div class="hidden md:block">Desktop only</div>

<!-- Show on mobile only -->
<div class="block md:hidden">Mobile only</div>

<!-- Responsive padding -->
<div class="px-4 md:px-6 py-4 md:py-8">
  <!-- Content -->
</div>
```

---

## ✅ Best Practices

### DO ✅
- Use consistent spacing scale (1, 2, 3, 4)
- Keep padding minimal for data-heavy views
- Use `text-xs` for table cells
- Use `px-3 py-2` for table cells
- Use `px-2 py-1` for compact buttons
- Add hover states to interactive elements
- Use semantic color classes
- Maintain visual hierarchy
- Add tooltips for icon-only buttons

### DON'T ❌
- Don't use large padding (px-6 py-4) in tables
- Don't use text-sm or larger in table cells
- Don't skip hover states
- Don't mix spacing scales inconsistently
- Don't use custom colors without reason
- Don't forget mobile responsiveness
- Don't use emojis in production labels

---

## 🚀 Quick Copy Templates

### Product List Row
```html
<tr class="hover:bg-gray-50">
  <td class="px-3 py-2 whitespace-nowrap">
    <div class="flex items-center">
      <img src="..." class="h-8 w-8 rounded object-cover mr-2">
      <div class="text-xs font-medium text-gray-900">Product Name</div>
    </div>
  </td>
  <td class="px-3 py-2 whitespace-nowrap">
    <div class="text-xs text-gray-700">Category</div>
  </td>
  <td class="px-3 py-2 whitespace-nowrap text-right">
    <div class="text-xs font-semibold text-gray-900">Rp 25,000</div>
  </td>
  <td class="px-3 py-2 whitespace-nowrap text-center">
    <span class="px-1.5 py-0.5 bg-green-100 text-green-700 text-xs rounded">Active</span>
  </td>
  <td class="px-3 py-2 whitespace-nowrap text-center">
    <div class="flex items-center justify-center gap-1">
      <a href="#" class="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700" title="View">👁️</a>
      <a href="#" class="px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700" title="Edit">✏️</a>
    </div>
  </td>
</tr>
```

### Filter Section (Ultra-Compact)
```html
<div class="bg-white rounded-lg shadow p-2.5 mb-1.5">
  <form method="get" class="grid grid-cols-1 md:grid-cols-4 gap-2">
    <div>
      <label class="block text-xs font-medium text-gray-700 mb-0.5">Search</label>
      <input type="text" name="search" 
             class="w-full px-2.5 py-1.5 text-xs border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
             placeholder="Search...">
    </div>
    <div class="flex items-end">
      <button type="submit" 
              class="w-full px-2.5 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg">
        Apply
      </button>
    </div>
  </form>
</div>
```

---

## 📌 Implementation Checklist

When creating new list/table pages (Ultra-Compact):
- [ ] Use ultra-compact container padding `px-4 py-1.5`
- [ ] Set section spacing to `mb-1.5` or `mb-2`
- [ ] Use `text-xs` for ALL text (headers, labels, cells, buttons)
- [ ] Apply `px-3 py-2` for table cell padding
- [ ] Use `px-2 py-1` or `px-2.5 py-1.5` for buttons
- [ ] Use `p-1.5` for stat cards, `p-2.5` for filter sections
- [ ] Use `gap-1.5` or `gap-2` for grids/flex
- [ ] Use `mb-0.5` for label spacing
- [ ] Page title: `text-xl` (not text-2xl)
- [ ] Stats numbers: `text-lg` (not text-2xl)
- [ ] Add hover states to interactive elements
- [ ] Include responsive breakpoints (md:, lg:)
- [ ] Add appropriate focus states to inputs
- [ ] Use semantic colors (blue, green, red, etc.)
- [ ] Test on mobile viewport
- [ ] Add tooltips for icon-only buttons
- [ ] Include loading states where needed
- [ ] Validate accessibility (ARIA labels, keyboard navigation)

---

**Last Updated:** January 19, 2026
**Version:** 2.0.0 (Ultra-Compact)

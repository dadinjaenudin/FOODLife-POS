# Queue Display Menu - Sidebar Integration

## 📍 Posisi Menu

```
┌─────────────────┐
│   🏠 LOGO      │
├─────────────────┤
│                 │
│  ⏰ Shift       │  ← Shift Status (auto-refresh)
│                 │
├─────────────────┤
│  📊 My Shift   │  ← Shift Reports
│  🖨️ Reprint    │
├─────────────────┤
│  🍳 Kitchen    │  ← Kitchen Stations
│  🍹 Bar        │
│  🍰 Dessert    │
├─────────────────┤
│  📺 Queue      │  ← **NEW! Queue Display**
├─────────────────┤
│                 │
│  👤 Profile    │  ← Bottom Actions
│  🚪 Logout     │
└─────────────────┘
```

## 🎨 Visual Design

### Queue Button:
- **Icon**: 📺 TV Monitor SVG
- **Text**: "Queue"
- **Color**: Amber-500 → Orange-600 gradient
- **Hover**: Amber-400 → Orange-500 (lighter)
- **Shadow**: Amber glow effect
- **Animation**: Shine effect on hover
- **Target**: Opens in new tab

### Code:
```html
<a href="{% url 'pos:queue_display' %}" target="_blank"
    class="relative w-full py-2.5 px-3 text-xs font-bold text-white 
           bg-gradient-to-r from-amber-500 to-orange-600 
           hover:from-amber-400 hover:to-orange-500 
           rounded-lg transition-all duration-300 
           shadow-md hover:shadow-amber-500/50 
           hover:-translate-y-0.5 active:scale-95 
           text-center block overflow-hidden group"
    title="Queue Display (TV Monitor)">
    <span class="relative z-10 flex items-center justify-center gap-1">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z">
            </path>
        </svg>
        Queue
    </span>
    <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent 
                transform -skew-x-12 -translate-x-full group-hover:translate-x-full 
                transition-transform duration-1000">
    </div>
</a>
```

## 🚀 Usage Flow

### For Cashier:
1. Open POS: `http://127.0.0.1:8000/pos/`
2. Click "Queue" button in left sidebar
3. New tab opens with Queue Display
4. Leave tab open on 2nd monitor

### For TV Display:
1. Cashier opens Queue Display
2. Press F11 for fullscreen
3. Position monitor facing customers
4. Auto-refresh every 5 seconds
5. Customers watch for their queue number

## 📊 Comparison with Other Buttons

| Button     | Color            | Use Case                    |
|------------|------------------|-----------------------------|
| **Queue**  | Amber → Orange   | Customer display (NEW!)     |
| Kitchen    | Orange → Red     | Kitchen station             |
| Bar        | Indigo → Purple  | Bar station                 |
| Dessert    | Pink → Rose      | Dessert station             |
| My Shift   | Purple → Pink    | Cashier dashboard           |
| Reprint    | White/10         | Reprint reconciliation      |

## ✅ Features

- **Distinctive Color**: Amber/Orange (not used by others)
- **Clear Icon**: TV Monitor (📺) 
- **New Tab**: Opens separately (target="_blank")
- **Tooltip**: "Queue Display (TV Monitor)"
- **Accessible**: Easy to find, logical position
- **Professional**: Matches sidebar design language

## 🎯 Benefits

1. **Easy Access**: One click from POS
2. **Multi-Monitor**: Works on 2nd screen
3. **Real-Time**: Auto-refresh (5 sec)
4. **Customer-Facing**: TV display ready
5. **No Setup**: Just click and go

---

**Status**: ✅ Implemented  
**File Modified**: `templates/pos/main.html`  
**Testing**: All checks passed  
**Ready**: Production-ready

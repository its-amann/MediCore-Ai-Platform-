# Workflow Progress Visual Specifications

## Design Mockups & Component Specifications

### 1. Overall Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                      Workflow Progress                           │
│          Real-time medical imaging analysis pipeline             │
│  ┌─────────────────────────────────────┐  [🛜 Live] [👁️]      │
│  │ Overall Progress         87%        │                        │
│  │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░  │          │                        │
│  │ Elapsed: 1:23   Est. Remaining: 0:15│                        │
│  └─────────────────────────────────────┘                        │
│                                                                  │
│  ┌─────────────────────────────────────┐                        │
│  │ ● 📤 Image Upload                   │ ✓ 0:05                │
│  │   Uploading and preprocessing       │                        │
│  └─────────────────────────────────────┘                        │
│             ═══════════════                                      │
│  ┌─────────────────────────────────────┐                        │
│  │ ● 📊 AI Analysis                    │ ✓ 0:18                │
│  │   Detecting coordinates...          │                        │
│  └─────────────────────────────────────┘                        │
│             ═══════════════                                      │
│  ┌─────────────────────────────────────┐                        │
│  │ ◉ 🎨 Heatmap Generation            │ ⏱️ In Progress         │
│  │   Creating attention heatmaps       │                        │
│  │   ▓▓▓▓▓▓▓▓▓░░░░░░░░░░ 45%         │                        │
│  └─────────────────────────────────────┘                        │
│             ═ ═ ═ ═ ═ ═ ═                                        │
│  ┌─────────────────────────────────────┐                        │
│  │ ○ 🤝 Multi-Agent Analysis          │ Est. 30-60s            │
│  │   Expert AI agents collaborating    │                        │
│  └─────────────────────────────────────┘                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Stage Status Indicators

#### Pending State
```
○ ────  Gray circle, static
        No animation
        Estimated time shown
```

#### Processing State
```
◉ ────  Blue pulsing circle
        Rotating animation
        Progress bar visible
        Live timer
```

#### Completed State
```
● ────  Green circle with checkmark
        Static, no animation
        Completion time shown
```

#### Error State
```
⊗ ────  Red circle with X
        Static, error message
        Retry button available
```

### 3. Multi-Agent Stage (Expanded View)

```
┌──────────────────────────────────────────────────────┐
│ 🤝 Multi-Agent Analysis                              │
│ Expert AI agents collaborating on report             │
│                                                      │
│ AI Agents Activity:                                  │
│ ┌──────────────────────────────────────────────┐   │
│ │ 🧠 Radiologist AI          ● Working...      │   │
│ │ 📊 Researcher AI           ✓ Completed       │   │
│ │ 🏥 Clinical Advisor        ○ Waiting         │   │
│ │ 📝 Report Writer           ○ Waiting         │   │
│ │ ✅ Quality Checker         ○ Waiting         │   │
│ └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

### 4. WebSocket Status Indicators

#### Connected
```
[🟢 Live]  Green dot with pulse animation
           "Live" text in green
```

#### Disconnected
```
[🔴 Disconnected]  Red dot, static
                   "Disconnected" text in red
                   Auto-reconnect countdown
```

#### Connecting
```
[🟡 Connecting...]  Yellow dot with spin
                    "Connecting..." text
```

### 5. Log Panel (Collapsed/Expanded)

```
┌──────────────────────────────────────────────────────┐
│ 🐛 Detailed Logs                      [Export ⬇️]   │
├──────────────────────────────────────────────────────┤
│ [10:23:45] ✅ Connected to workflow server          │
│ [10:23:46] 🔄 Image Upload: processing              │
│ [10:23:51] 🔄 Image Upload: completed               │
│ [10:23:51] 🔄 AI Analysis: processing               │
│ [10:24:09] 🤖 Radiologist AI: active                │
│ [10:24:12] 🤖 Researcher AI: active                 │
│ └────────────────────────────────────────────────┘ │
│                    ▼ (scroll)                        │
└──────────────────────────────────────────────────────┘
```

### 6. Completion Actions

```
┌──────────────────────────────────────────┐
│    ✅ Workflow Completed Successfully!    │
│                                          │
│  [📥 Download Report] [🔗 Share] [🔄 New] │
└──────────────────────────────────────────┘
```

## Animation Specifications

### 1. Stage Transitions
- **Entry**: Fade in + slide from left (0.3s ease-out)
- **Progress Update**: Smooth transition (0.2s ease-in-out)
- **Completion**: Scale bounce (1.0 → 1.1 → 1.0, 0.3s)

### 2. Connection Lines
- **Inactive**: Static gray line
- **Active**: Shimmer animation left-to-right (1s loop)
- **Complete**: Fade from gray to blue (0.5s)

### 3. Progress Bars
- **Fill Animation**: Linear fill with gradient (smooth)
- **Shimmer Effect**: 45° gradient sweep (1s loop)

### 4. Status Badges
- **Processing Pulse**: Scale 1.0 → 1.2 → 1.0 (1.5s loop)
- **Error Shake**: Horizontal shake 3 times (0.3s)

## Responsive Breakpoints

### Desktop (>1200px)
- Horizontal layout with connection lines
- Full agent details visible
- Side-by-side preview images

### Tablet (768px - 1200px)
- Vertical stage layout
- Collapsed agent view by default
- Stacked preview images

### Mobile (<768px)
- Single column layout
- No connection lines
- Simplified animations
- Bottom sheet for logs

## Color Specifications

```scss
// Primary Colors
$primary: #6366f1;      // Indigo
$secondary: #8b5cf6;    // Purple
$accent: #ec4899;       // Pink

// Status Colors
$success: #10b981;      // Emerald
$warning: #f59e0b;      // Amber
$error: #ef4444;        // Red
$info: #3b82f6;         // Blue

// Neutral Colors
$gray-50: rgba(255, 255, 255, 0.05);
$gray-100: rgba(255, 255, 255, 0.1);
$gray-200: rgba(255, 255, 255, 0.2);
$gray-300: rgba(255, 255, 255, 0.3);
$gray-400: rgba(255, 255, 255, 0.4);
$gray-500: rgba(255, 255, 255, 0.5);
$gray-600: rgba(255, 255, 255, 0.6);
$gray-700: rgba(255, 255, 255, 0.7);
$gray-800: rgba(255, 255, 255, 0.8);
$gray-900: rgba(255, 255, 255, 0.9);

// Glassmorphism
$glass-bg: rgba(255, 255, 255, 0.05);
$glass-border: rgba(255, 255, 255, 0.1);
$glass-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
$backdrop-blur: 10px;
```

## Typography

```scss
// Font Family
$font-primary: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
$font-mono: 'SF Mono', Monaco, Consolas, 'Courier New', monospace;

// Font Sizes
$text-xs: 0.75rem;    // 12px
$text-sm: 0.875rem;   // 14px
$text-base: 1rem;     // 16px
$text-lg: 1.125rem;   // 18px
$text-xl: 1.25rem;    // 20px
$text-2xl: 1.5rem;    // 24px
$text-3xl: 1.875rem;  // 30px

// Font Weights
$font-normal: 400;
$font-medium: 500;
$font-semibold: 600;
$font-bold: 700;

// Line Heights
$leading-tight: 1.25;
$leading-snug: 1.375;
$leading-normal: 1.5;
$leading-relaxed: 1.625;
```

## Spacing System

```scss
// Base unit: 4px
$space-1: 0.25rem;   // 4px
$space-2: 0.5rem;    // 8px
$space-3: 0.75rem;   // 12px
$space-4: 1rem;      // 16px
$space-5: 1.25rem;   // 20px
$space-6: 1.5rem;    // 24px
$space-8: 2rem;      // 32px
$space-10: 2.5rem;   // 40px
$space-12: 3rem;     // 48px
$space-16: 4rem;     // 64px
```

## Component States

### Hover States
- Lift shadow: translateY(-2px)
- Brighten background: +5% opacity
- Show additional controls

### Focus States
- Blue outline: 2px solid $primary
- Increased contrast
- Keyboard navigation indicators

### Loading States
- Skeleton screens for content
- Shimmer animation
- Progressive disclosure

### Error States
- Red border and background tint
- Error icon and message
- Retry action button

## Accessibility Guidelines

1. **Color Contrast**
   - Text on glass: minimum 4.5:1 ratio
   - Interactive elements: minimum 3:1 ratio
   - Error states: distinct patterns beyond color

2. **Keyboard Navigation**
   - Tab order follows visual hierarchy
   - Focus indicators clearly visible
   - Escape key closes expanded sections

3. **Screen Reader Support**
   - ARIA labels for all stages
   - Live regions for status updates
   - Descriptive button labels

4. **Motion Preferences**
   - Respect prefers-reduced-motion
   - Provide static alternatives
   - Essential animations only
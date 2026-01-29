# UI2 - Skype-Inspired Modern Design

## Overview

This folder contains a complete redesign of the LAN Conference UI with a modern, Skype-inspired aesthetic.

## Design Philosophy

### Visual Principles

- **Clean & Minimal**: Generous whitespace, reduced visual clutter
- **Soft Rounded Elements**: 8-12px border radius for modern feel
- **Subtle Shadows**: Depth through soft shadows, not harsh borders
- **Calm Color Palette**: Light backgrounds with Skype blue (#0078d4) accents
- **Accessible Contrast**: WCAG AA compliant color combinations

### Key Changes from Original

#### Color Palette

- **Primary**: #0078d4 (Skype Blue) - replaces #00aaff
- **Success**: #107c10 (Green) - replaces #43b581
- **Error**: #e81123 (Red) - replaces #ed4245
- **Warning**: #ffb900 (Amber) - replaces #ffc107
- **Background**: #f0f0f0, #fafafa, #ffffff (Light grays)
- **Text**: #242424 (Dark gray) - replaces white text

#### Typography

- **Font Family**: 'Segoe UI', 'SF Pro Display', system fonts
- **Font Weights**: 400 (regular), 500 (medium), 600 (semibold)
- **Font Sizes**: 11-15px with improved line-height (1.4-1.6)
- **Letter Spacing**: Subtle adjustments for readability

#### Spacing & Layout

- **Padding**: Increased from 8-10px to 12-16px
- **Margins**: More generous spacing between elements
- **Border Radius**: Increased from 4-6px to 8-12px
- **Control Buttons**: Larger (52x52px vs 44x44px)

#### Interactive States

- **Hover**: Subtle background color change (#f3f3f3 → #e8e8e8)
- **Active/Pressed**: Darker shade (#e8e8e8 → #d8d8d8)
- **Focus**: 2px Skype blue border
- **Disabled**: Lighter background with reduced opacity

#### Components

##### Login Dialog

- Larger, more spacious layout (480x680px)
- Smooth fade animations between pages
- Modern input fields with focus states
- Prominent action buttons

##### Main Window

- Light theme with white panels
- Refined video tiles with soft shadows
- Modern control bar with circular buttons
- Clean tab interface

##### Chat Interface

- Light chat bubbles with subtle borders
- Improved message spacing
- Modern input field with rounded corners
- File transfer cards with clean design

##### Participant List

- Larger avatars (44x44px)
- Better status indicators
- Hover effects for interactivity
- Clean typography

### Micro-Interactions

- Smooth hover transitions (200ms)
- Fade animations for page changes
- Scale transforms on button press
- Opacity changes for disabled states

## Files

### styles.py

Complete stylesheet with:

- Main application styles
- Login dialog styles
- Component-specific styles
- Responsive scrollbars

### login_dialog.py

Modern login interface with:

- Smooth page transitions
- Refined input fields
- Better error handling
- Improved typography

### private_chat.py

Clean 1:1 chat interface with:

- Modern message bubbles
- Refined header design
- Smooth animations
- Better spacing

### main_window.py

Main application window with:

- Light theme styling
- Modern controls
- Refined components
- Better visual hierarchy

## Usage

To use the new UI, update your client imports:

```python
# Change from:
from ui.main_window import EnhancedMainWindow

# To:
from ui2.main_window import EnhancedMainWindow
```

Or update the client.py file to import from ui2 instead of ui.

## Comparison

| Aspect        | Original (ui/) | Redesigned (ui2/) |
| ------------- | -------------- | ----------------- |
| Theme         | Dark           | Light             |
| Primary Color | #00aaff        | #0078d4           |
| Border Radius | 4-6px          | 8-12px            |
| Padding       | 8-10px         | 12-16px           |
| Font Weight   | 600-700        | 500-600           |
| Shadows       | Minimal        | Subtle, layered   |
| Animations    | Basic          | Smooth, polished  |

## Browser/Platform Support

- macOS: Full support with SF Pro Display
- Windows: Full support with Segoe UI
- Linux: Falls back to system sans-serif

## Accessibility

- WCAG AA contrast ratios
- Keyboard navigation support
- Screen reader friendly labels
- Focus indicators on all interactive elements

## Future Enhancements

- Dark mode toggle
- Custom theme colors
- Animation speed preferences
- Compact/comfortable density options

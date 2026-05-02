---
name: Bassira Causse
colors:
  surface: '#fff8f6'
  surface-dim: '#ebd6cf'
  surface-bright: '#fff8f6'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fff1ec'
  surface-container: '#ffe9e2'
  surface-container-high: '#f9e4dd'
  surface-container-highest: '#f3ded7'
  on-surface: '#241915'
  on-surface-variant: '#57423a'
  inverse-surface: '#3a2e29'
  inverse-on-surface: '#ffede7'
  outline: '#8a7269'
  outline-variant: '#dec0b6'
  surface-tint: '#a13f0f'
  primary: '#7e2b00'
  on-primary: '#ffffff'
  primary-container: '#a13f0f'
  on-primary-container: '#ffcdbb'
  inverse-primary: '#ffb599'
  secondary: '#a13f0f'
  on-secondary: '#ffffff'
  secondary-container: '#fd8450'
  on-secondary-container: '#6c2400'
  tertiary: '#005132'
  on-tertiary: '#ffffff'
  tertiary-container: '#006c43'
  on-tertiary-container: '#91eab7'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbce'
  primary-fixed-dim: '#ffb599'
  on-primary-fixed: '#370e00'
  on-primary-fixed-variant: '#7f2b00'
  secondary-fixed: '#ffdbce'
  secondary-fixed-dim: '#ffb598'
  on-secondary-fixed: '#370e00'
  on-secondary-fixed-variant: '#7f2b00'
  tertiary-fixed: '#9cf5c1'
  tertiary-fixed-dim: '#80d8a6'
  on-tertiary-fixed: '#002111'
  on-tertiary-fixed-variant: '#005232'
  background: '#fff8f6'
  on-background: '#241915'
  surface-variant: '#f3ded7'
typography:
  h1:
    fontFamily: Outfit
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  h2:
    fontFamily: Outfit
    fontSize: 36px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  h3:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
    letterSpacing: '0'
  body-lg:
    fontFamily: Manrope
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.2'
  arabic-body:
    fontFamily: Tajawal
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.8'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 48px
  xl: 80px
  container-max: 1280px
  gutter: 32px
---

## Brand & Style

This design system establishes a sophisticated visual bridge between MENA heritage and European modernism. It is built on the philosophy of **"Authority without Coldness,"** blending the mathematical precision of Bauhaus minimalism with the tactile, organic luxury of Mediterranean and Saharan craftsmanship.

The target audience consists of high-discerning professionals and institutional entities who value clarity, heritage, and modern efficiency. The UI should evoke a sense of "Artisanal Luxury"—where every pixel feels intentional and every interaction feels calm. This is achieved through a strict adherence to geometric structures, generous whitespace that acts as a canvas for high-quality content, and a color palette that avoids the clinical sterility of pure black and white in favor of warm, grounded tones.

## Colors

The palette is rooted in earth and light, eschewing the aggressive digital hues typical of modern SaaS. 

- **Primary Background (#FAF7F2):** A "Cream Off-White" that serves as the tactile base, reminiscent of premium stationery or refined limestone.
- **Primary Text (#241915):** A "Warm Charcoal-Brown" used for all primary communication to maintain authority while appearing more organic and softer than pure black.
- **Primary Action (#A13F0F):** "Deep Terracotta" is the anchor for critical CTAs, representing earth, construction, and grounded ambition.
- **Secondary Action (#FF8551):** A "Warm Orange" used for highlights and secondary interactions to provide a sun-drenched vibrancy.
- **Success/Trust (#006D44):** A "Deep Mint-Green" that signals growth and reliability, carefully balanced to avoid clashing with the terracotta.

## Typography

The typography system is dual-natured: geometric authority for structure and high-legibility for utility. 

- **Outfit** provides a structural, Bauhaus-inspired geometric rhythm for headlines. Use tighter letter-spacing for large display sizes to increase the feeling of "Authority."
- **Manrope** is the workhorse for body copy and UI elements, offering a professional, balanced tone that bridges the gap between technical and human.
- **JetBrains Mono** is utilized for technical data, metadata, and labels, reinforcing the brand's precision and transparency.
- **Tajawal** ensures the Arabic script maintains the same geometric cleanliness as the Latin counterparts, prioritizing legibility and cultural resonance.

For long-form editorial content, increase the line height to 1.8 to allow the "Cream Off-White" background to breathe through the text.

## Layout & Spacing

This design system utilizes a **Fixed Grid** model for desktop, centered within the viewport to create an editorial feel. The spacing philosophy is built on a 8px geometric scale, but emphasizes "generous breathing room."

- **Margins:** Large outer margins (xl) are mandatory for top-level pages to maintain a premium "gallery" aesthetic.
- **Gutter:** Use a 32px gutter to ensure that even dense data-rich layouts do not feel cramped.
- **Rhythm:** Vertical spacing should be used aggressively to separate distinct content blocks. Avoid crowding components; if in doubt, increase the spacing to the next scale level.

## Elevation & Depth

To maintain the "Bauhaus Minimalism" aesthetic, depth is created through **Tonal Layers** rather than heavy shadows. 

- **Surface Tiers:** Use subtle variations of the background color or very thin (1px) borders in the Primary Text color at low opacity (10-15%) to define containers.
- **Shadows:** When shadows are necessary for functional elevation (e.g., dropdowns), use "Ambient Shadows"—diffused, long-range blurs with very low opacity, tinted with the Deep Terracotta (#A13F0F) at 5% to keep the warmth consistent.
- **Flatness:** Primary surfaces should feel integrated into the "Cream" floor, not floating above it.

## Shapes

The shape language is **"Rounded" (Level 2)**. 

This level of curvature (0.5rem base) softens the geometric rigidity of the typography, contributing to the "Authority without coldness" narrative. It suggests an artisanal quality—like hand-polished stone or molded leather—rather than the sharp, industrial edges of pure minimalism or the overly playful "bubbly" appearance of consumer apps. 

Containers use `rounded-lg` (1rem) while interactive elements like buttons use the base `rounded` (0.5rem).

## Components

- **Buttons:** Primary buttons use a solid Deep Terracotta (#A13F0F) fill with White text. Secondary buttons use a 1px border of the Warm Charcoal-Brown with a slight hover state transition to the Secondary Action color.
- **Chips/Badges:** Utilize the Deep Mint-Green (#006D44) for status indicators, paired with JetBrains Mono for the text to emphasize technical accuracy.
- **Input Fields:** Use a subtle 1px border in the Charcoal-Brown (20% opacity). On focus, the border transitions to Deep Terracotta. The background remains the Primary Background color to feel "etched" into the UI.
- **Cards:** Eschew heavy shadows. Use a 1px border or a very slight tonal shift. Content within cards should follow the editorial layout rules—large headers and clear mono-spaced labels.
- **Arabic Integration:** All components must support Right-to-Left (RTL) mirroring, ensuring that the visual weight of the "Deep Terracotta" actions remains balanced in both MENA and European contexts.
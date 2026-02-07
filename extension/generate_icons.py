"""
Generate professional extension icons for LinkedIn Job Auto-Fill Pro.
Creates PNG icons in multiple sizes with a modern, professional design.
"""

import os

def generate_icon_svg(size):
    """Generate SVG icon for the extension - a stylized briefcase with checkmark."""
    
    # Scale factor for different sizes
    scale = size / 128
    
    # LinkedIn blue color palette
    primary_color = "#0A66C2"  # LinkedIn blue
    secondary_color = "#00A0DC"  # Lighter blue
    accent_color = "#057642"  # Green for checkmark
    white = "#FFFFFF"
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 128 128">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{primary_color};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{secondary_color};stop-opacity:1" />
    </linearGradient>
    <linearGradient id="checkGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#10B981;stop-opacity:1" />
      <stop offset="100%" style="stop-color:{accent_color};stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Background circle -->
  <circle cx="64" cy="64" r="60" fill="url(#bgGrad)"/>
  
  <!-- Briefcase body -->
  <rect x="24" y="42" width="80" height="56" rx="8" ry="8" fill="{white}" opacity="0.95"/>
  
  <!-- Briefcase handle -->
  <path d="M48 42 L48 32 Q48 24 56 24 L72 24 Q80 24 80 32 L80 42" 
        fill="none" stroke="{white}" stroke-width="6" stroke-linecap="round"/>
  
  <!-- Briefcase center line -->
  <rect x="58" y="52" width="12" height="36" rx="2" fill="{primary_color}" opacity="0.3"/>
  
  <!-- Checkmark circle -->
  <circle cx="90" cy="82" r="22" fill="url(#checkGrad)"/>
  
  <!-- Checkmark -->
  <path d="M80 82 L87 89 L102 74" 
        fill="none" stroke="{white}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  
  <!-- Lightning bolt (auto-fill symbol) -->
  <path d="M52 56 L46 70 L54 70 L48 84 L62 66 L54 66 L60 56 Z" 
        fill="{primary_color}" opacity="0.6"/>
</svg>'''
    
    return svg


def generate_simple_icon_svg(size):
    """Generate a simpler, cleaner icon that works well at small sizes."""
    
    primary_color = "#0A66C2"
    accent_color = "#10B981"
    white = "#FFFFFF"
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 128 128">
  <defs>
    <linearGradient id="mainGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0077B5;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#00A0DC;stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Rounded square background -->
  <rect x="4" y="4" width="120" height="120" rx="24" ry="24" fill="url(#mainGrad)"/>
  
  <!-- Document/Form icon -->
  <rect x="32" y="24" width="48" height="64" rx="4" ry="4" fill="{white}"/>
  
  <!-- Document lines -->
  <rect x="40" y="36" width="32" height="4" rx="2" fill="{primary_color}" opacity="0.3"/>
  <rect x="40" y="48" width="24" height="4" rx="2" fill="{primary_color}" opacity="0.3"/>
  <rect x="40" y="60" width="28" height="4" rx="2" fill="{primary_color}" opacity="0.3"/>
  <rect x="40" y="72" width="20" height="4" rx="2" fill="{primary_color}" opacity="0.3"/>
  
  <!-- Checkmark badge -->
  <circle cx="88" cy="80" r="28" fill="{accent_color}"/>
  <path d="M74 80 L84 90 L104 70" 
        fill="none" stroke="{white}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
  
  <!-- Small "A" for Auto -->
  <text x="54" y="106" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="{white}" text-anchor="middle">A</text>
</svg>'''
    
    return svg


def main():
    """Generate icons in all required sizes."""
    
    icons_dir = os.path.dirname(os.path.abspath(__file__))
    icons_folder = os.path.join(icons_dir, "icons")
    
    # Ensure icons folder exists
    os.makedirs(icons_folder, exist_ok=True)
    
    sizes = [16, 32, 48, 128]
    
    print("Generating extension icons...")
    
    for size in sizes:
        # Use simpler icon for small sizes, detailed for large
        if size <= 32:
            svg_content = generate_simple_icon_svg(size)
        else:
            svg_content = generate_simple_icon_svg(size)
        
        # Save SVG
        svg_path = os.path.join(icons_folder, f"icon{size}.svg")
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        print(f"  ✓ Generated icon{size}.svg")
    
    print("\n✓ SVG icons generated!")
    print("\nTo convert to PNG (required for Chrome):")
    print("  Option 1: Use online converter like svgtopng.com")
    print("  Option 2: Install cairosvg: pip install cairosvg")
    print("            Then run: python -c \"import cairosvg; cairosvg.svg2png(url='icon128.svg', write_to='icon128.png')\"")
    
    # Try to convert to PNG if cairosvg is available
    try:
        import cairosvg
        print("\n  cairosvg found! Converting to PNG...")
        for size in sizes:
            svg_path = os.path.join(icons_folder, f"icon{size}.svg")
            png_path = os.path.join(icons_folder, f"icon{size}.png")
            cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=size, output_height=size)
            print(f"    ✓ Converted icon{size}.png")
        print("\n✓ PNG icons generated successfully!")
    except ImportError:
        print("\n  (cairosvg not installed - PNG conversion skipped)")
        print("  Install with: pip install cairosvg")


if __name__ == "__main__":
    main()

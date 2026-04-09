from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math

def create_glowing_door(size=800, include_text=True, text="JANOVUM", circle_crop=False):
    """Recreate the glowing door/arch design"""
    img = Image.new('RGBA', (size, size), (15, 20, 35, 255))
    draw = ImageDraw.Draw(img)
    
    cx, cy = size // 2, size // 2
    
    # Door dimensions
    door_w = int(size * 0.52)
    door_h = int(size * 0.62)
    arch_radius = door_w // 2
    
    # Position door higher to leave room for text or center if no text
    if include_text:
        door_top = int(size * 0.08)
    else:
        door_top = int(size * 0.12)
    
    door_left = cx - door_w // 2
    door_right = cx + door_w // 2
    door_bottom = door_top + door_h
    arch_center_y = door_top + arch_radius
    
    # --- Glow layers (outer to inner) ---
    glow_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    
    for i in range(25, 0, -1):
        alpha = int(8 + (25 - i) * 2)
        expand = i * 3
        color = (100, 180, 255, alpha)
        
        # Arch glow
        glow_draw.ellipse([
            door_left - expand, arch_center_y - arch_radius - expand,
            door_right + expand, arch_center_y + arch_radius + expand
        ], outline=color, width=2)
        
        # Rectangle glow
        glow_draw.rectangle([
            door_left - expand, arch_center_y,
            door_right + expand, door_bottom + expand
        ], outline=color, width=2)
    
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=15))
    img = Image.alpha_composite(img, glow_img)
    draw = ImageDraw.Draw(img)
    
    # --- Inner dark door fill ---
    # Fill the arch (top half circle)
    draw.ellipse([
        door_left, arch_center_y - arch_radius,
        door_right, arch_center_y + arch_radius
    ], fill=(20, 25, 40, 255))
    
    # Fill the rectangle part
    draw.rectangle([
        door_left, arch_center_y,
        door_right, door_bottom
    ], fill=(20, 25, 40, 255))
    
    # --- Center glow (subtle light from within) ---
    center_glow = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    cg_draw = ImageDraw.Draw(center_glow)
    glow_cy = arch_center_y + int(door_h * 0.15)
    for r in range(int(size * 0.2), 0, -2):
        alpha = int(30 * (1 - r / (size * 0.2)))
        cg_draw.ellipse([cx - r, glow_cy - r, cx + r, glow_cy + r], 
                        fill=(180, 200, 240, alpha))
    center_glow = center_glow.filter(ImageFilter.GaussianBlur(radius=30))
    img = Image.alpha_composite(img, center_glow)
    draw = ImageDraw.Draw(img)
    
    # --- Door border (bright blue outline) ---
    border_color = (120, 200, 255, 220)
    border_w = max(2, size // 200)
    
    # Arch outline
    draw.arc([
        door_left, arch_center_y - arch_radius,
        door_right, arch_center_y + arch_radius
    ], start=180, end=0, fill=border_color, width=border_w)
    
    # Side lines
    draw.line([(door_left, arch_center_y), (door_left, door_bottom)], fill=border_color, width=border_w)
    draw.line([(door_right, arch_center_y), (door_right, door_bottom)], fill=border_color, width=border_w)
    
    # Bottom line
    draw.line([(door_left, door_bottom), (door_right, door_bottom)], fill=border_color, width=border_w)
    
    # --- Tick marks on the arch (like the original) ---
    num_ticks = 60
    for i in range(num_ticks):
        angle = math.pi + (math.pi * i / (num_ticks - 1))
        inner_r = arch_radius - 2
        outer_r = arch_radius + int(size * 0.015)
        
        x1 = cx + inner_r * math.cos(angle)
        y1 = arch_center_y + inner_r * math.sin(angle)
        x2 = cx + outer_r * math.cos(angle)
        y2 = arch_center_y + outer_r * math.sin(angle)
        
        tick_alpha = 180 if i % 5 == 0 else 100
        draw.line([(x1, y1), (x2, y2)], fill=(200, 220, 255, tick_alpha), width=1)
    
    # --- Bottom triangle/light beam ---
    tri_top = door_bottom + 2
    tri_h = int(size * 0.06)
    tri_w = int(door_w * 0.35)
    
    tri_glow = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    tg_draw = ImageDraw.Draw(tri_glow)
    tg_draw.polygon([
        (cx - tri_w, tri_top),
        (cx + tri_w, tri_top),
        (cx, tri_top + tri_h)
    ], fill=(180, 220, 255, 150))
    tri_glow = tri_glow.filter(ImageFilter.GaussianBlur(radius=5))
    img = Image.alpha_composite(img, tri_glow)
    draw = ImageDraw.Draw(img)
    
    # --- Text ---
    if include_text:
        try:
            font_size = int(size * 0.09)
            font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        text_y = tri_top + tri_h + int(size * 0.02)
        
        # Text glow
        text_glow = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        tgd = ImageDraw.Draw(text_glow)
        bbox = tgd.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        text_x = cx - tw // 2
        tgd.text((text_x, text_y), text, fill=(100, 180, 255, 100), font=font)
        text_glow = text_glow.filter(ImageFilter.GaussianBlur(radius=8))
        img = Image.alpha_composite(img, text_glow)
        draw = ImageDraw.Draw(img)
        
        # Main text
        draw.text((text_x, text_y), text, fill=(220, 235, 255, 255), font=font)
    
    # --- Circle crop for TikTok ---
    if circle_crop:
        mask = Image.new('L', (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, size, size], fill=255)
        
        result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        result.paste(img, (0, 0), mask)
        return result
    
    return img

# --- Generate PFP (square, with JANOVUM text, no MONITOR) ---
pfp = create_glowing_door(size=800, include_text=True, text="JANOVUM", circle_crop=False)
pfp_path = "C:/Users/jigga/OneDrive/Desktop/Janovum_PFP.png"
pfp.save(pfp_path)
print(f"Saved: {pfp_path}")

# --- Generate TikTok PFP (circle-cropped, no text for clean circle look) ---
tiktok = create_glowing_door(size=800, include_text=False, circle_crop=True)
tiktok_path = "C:/Users/jigga/OneDrive/Desktop/Janovum_TikTok_PFP.png"
tiktok.save(tiktok_path)
print(f"Saved: {tiktok_path}")

print("Done!")

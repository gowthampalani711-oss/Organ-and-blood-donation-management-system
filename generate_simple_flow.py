import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# 16:9 Widescreen slide
fig = plt.figure(figsize=(15, 6.2), dpi=300)
ax = plt.gca()
ax.set_xlim(0, 15)
ax.set_ylim(0, 6.2)
ax.axis('off')

# Background
fig.patch.set_facecolor('#FFFFFF')
ax.set_facecolor('#FFFFFF')

# Slide Title
plt.text(7.5, 5.5, "SYSTEM WORKFLOW (FLOW DIAGRAM)", 
         ha='center', va='center', fontsize=22, fontweight='bold', color='#1E293B', fontfamily='sans-serif')
plt.text(7.5, 5.0, "Organ & Blood Donation Management System", 
         ha='center', va='center', fontsize=12, color='#64748B', fontfamily='sans-serif')

# Step data: (Title, Line1, Line2, BgColor, BorderColor, StepNum)
steps = [
    ("1. REGISTRATION", "Donor & Patient Details", "Medical History / Form", "#EFF6FF", "#3B82F6", "01"),
    ("2. VERIFICATION", "Mobile OTP (Twilio)", "Medical Reports Check", "#FAF5FF", "#A855F7", "02"),
    ("3. DATABASE", "MySQL Central Storage", "Encrypted Patient Data", "#F0FDF4", "#22C55E", "03"),
    ("4. AI MATCHING", "Blood Group & Distance", "Emergency Priority Match", "#FFFBEB", "#F59E0B", "04"),
    ("5. OUTPUT & ALERT", "Digital QR Donor Card", "Hospital / Patient Alert", "#ECFDF5", "#10B981", "05")
]

box_w = 2.4
box_h = 2.4
y_pos = 1.8
start_x = 0.6
gap = 0.55

for i, (title, line1, line2, bg, border, num) in enumerate(steps):
    x = start_x + i * (box_w + gap)
    
    # Shadow
    shadow = FancyBboxPatch((x+0.05, y_pos-0.05), box_w, box_h, boxstyle="round,pad=0.08,rounding_size=0.15",
                            facecolor='#F1F5F9', edgecolor='none', zorder=2)
    ax.add_patch(shadow)
    
    # Main Box
    box = FancyBboxPatch((x, y_pos), box_w, box_h, boxstyle="round,pad=0.08,rounding_size=0.15",
                         facecolor=bg, edgecolor=border, linewidth=2.2, zorder=3)
    ax.add_patch(box)
    
    # Step Number Circle
    circle = plt.Circle((x + box_w/2, y_pos + box_h - 0.35), 0.32, color=border, zorder=4)
    ax.add_patch(circle)
    ax.text(x + box_w/2, y_pos + box_h - 0.35, num, color='#FFFFFF', fontsize=11, fontweight='bold',
            ha='center', va='center', zorder=5, fontfamily='sans-serif')
    
    # Step Title
    ax.text(x + box_w/2, y_pos + box_h - 0.95, title, color='#0F172A', fontsize=10.5, fontweight='bold',
            ha='center', va='center', zorder=4, fontfamily='sans-serif')
    
    # Divider line
    ax.plot([x+0.25, x+box_w-0.25], [y_pos + box_h - 1.2, y_pos + box_h - 1.2], color=border, linewidth=1, alpha=0.6, zorder=4)
    
    # Lines
    ax.text(x + box_w/2, y_pos + 0.68, f"• {line1}", color='#334155', fontsize=8.8,
            ha='center', va='center', zorder=4, fontfamily='sans-serif')
    ax.text(x + box_w/2, y_pos + 0.32, f"• {line2}", color='#334155', fontsize=8.8,
            ha='center', va='center', zorder=4, fontfamily='sans-serif')
    
    # Arrow to next box
    if i < len(steps) - 1:
        arrow_x1 = x + box_w + 0.05
        arrow_x2 = arrow_x1 + gap - 0.1
        arrow_y = y_pos + box_h / 2
        ax.annotate(
            '', xy=(arrow_x2, arrow_y), xytext=(arrow_x1, arrow_y),
            arrowprops=dict(arrowstyle="->,head_width=0.4,head_length=0.45", 
                            color="#64748B", lw=2.5),
            zorder=6
        )

# Bottom footer note
plt.text(7.5, 0.7, "Tech Stack: Python Flask | MySQL | Twilio OTP | AI Matching Algorithm | ReportLab QR PDF", 
         ha='center', va='center', fontsize=10.5, fontweight='600', color='#64748B', fontfamily='sans-serif')

out_path = r"c:\xampp1\htdocs\Organ Donation\simple_ppt_flow.png"
plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='#FFFFFF')
plt.close()
print("Generated simple flow diagram:", out_path)

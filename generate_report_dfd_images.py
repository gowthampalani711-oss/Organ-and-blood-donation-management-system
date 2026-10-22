import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle, Ellipse
import os

# Set font family to Times New Roman / serif
plt.rcParams['font.family'] = 'serif'
plt.rcParams['mathtext.fontset'] = 'dejavuserif'

out_dir = r"c:\xampp1\htdocs\Organ Donation"

def draw_split_circle(ax, cx, cy, rx, ry, pid, title_lines, fontsize=9):
    """Draws a classic Gane-Sarson / DeMarco split circle process bubble"""
    e = Ellipse((cx, cy), rx*2, ry*2, edgecolor='black', facecolor='white', linewidth=1.6, zorder=2)
    ax.add_patch(e)
    line_y = cy + ry*0.35
    chord_half = rx * (1 - (0.35)**2)**0.5
    ax.plot([cx - chord_half, cx + chord_half], [line_y, line_y], color='black', linewidth=1.6, zorder=3)
    
    # ID
    ax.text(cx, cy + ry*0.62, pid, ha='center', va='center', fontsize=fontsize+1, fontweight='bold', zorder=4)
    
    # Title
    if len(title_lines) == 1:
        ax.text(cx, cy - ry*0.2, title_lines[0], ha='center', va='center', fontsize=fontsize, fontweight='bold', zorder=4)
    elif len(title_lines) == 2:
        ax.text(cx, cy - ry*0.05, title_lines[0], ha='center', va='center', fontsize=fontsize, fontweight='bold', zorder=4)
        ax.text(cx, cy - ry*0.45, title_lines[1], ha='center', va='center', fontsize=fontsize, fontweight='bold', zorder=4)
    elif len(title_lines) == 3:
        ax.text(cx, cy + ry*0.08, title_lines[0], ha='center', va='center', fontsize=fontsize-0.8, fontweight='bold', zorder=4)
        ax.text(cx, cy - ry*0.22, title_lines[1], ha='center', va='center', fontsize=fontsize-0.8, fontweight='bold', zorder=4)
        ax.text(cx, cy - ry*0.52, title_lines[2], ha='center', va='center', fontsize=fontsize-0.8, fontweight='bold', zorder=4)

def draw_entity(ax, x, y, w, h, text, fontsize=10):
    """Draws external entity rectangle"""
    rect = Rectangle((x, y), w, h, edgecolor='black', facecolor='white', linewidth=1.6, zorder=2)
    ax.add_patch(rect)
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=fontsize, fontweight='bold', zorder=4)

def draw_datastore(ax, cx, cy, w, h, text, fontsize=8.5):
    """Draws open-ended datastore with double vertical side bars centered at (cx, cy)"""
    x = cx - w/2
    y = cy - h/2
    rect = Rectangle((x, y), w, h, edgecolor='black', facecolor='white', linewidth=1.6, zorder=2)
    ax.add_patch(rect)
    inset = 0.2
    ax.plot([x + inset, x + inset], [y, y + h], color='black', linewidth=1.6, zorder=3)
    ax.plot([x + w - inset, x + w - inset], [y, y + h], color='black', linewidth=1.6, zorder=3)
    ax.text(cx, cy, text, ha='center', va='center', fontsize=fontsize, fontweight='bold', zorder=4)

def draw_arrow(ax, x1, y1, x2, y2, label=None, label_pos=0.5, label_offset=(0, 0.12), label_fs=7.5):
    """Draws black arrow"""
    ax.annotate(
        '', xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(facecolor='black', edgecolor='black', arrowstyle='->', lw=1.4, shrinkA=0, shrinkB=0),
        zorder=1
    )
    if label:
        lx = x1 + (x2 - x1) * label_pos + label_offset[0]
        ly = y1 + (y2 - y1) * label_pos + label_offset[1]
        ax.text(lx, ly, label, ha='center', va='center', fontsize=label_fs, fontstyle='italic', zorder=5,
                bbox=dict(boxstyle='square,pad=0.15', fc='white', ec='none'))

# ==========================================================
# 1. GENERATE FIGURE 7.1: LEVEL 0 DFD (CONTEXT DIAGRAM)
# ==========================================================
fig, ax = plt.subplots(figsize=(9, 6.2), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 7)
ax.axis('off')

# Caption
ax.text(5.0, 0.4, "Figure 7.1 Level 0 data flow diagram", fontsize=12.5, fontweight='bold', fontstyle='italic', ha='center')

# Central Process 0.0
draw_split_circle(ax, 5.0, 3.6, 1.45, 1.25, "0.0", ["ORGAN & BLOOD", "DONATION", "MANAGEMENT SYSTEM"], fontsize=9)

# Entities
draw_entity(ax, 0.6, 4.6, 1.6, 0.75, "USER", fontsize=10)
draw_entity(ax, 0.6, 1.7, 1.6, 0.75, "ADMIN", fontsize=10)
draw_entity(ax, 7.8, 4.6, 1.6, 0.75, "HOSPITAL", fontsize=10)
draw_entity(ax, 7.8, 1.7, 1.6, 0.75, "SMS / EMAIL", fontsize=10)

# Arrows
draw_arrow(ax, 2.2, 5.15, 3.65, 4.3, "Donor / Patient Details", label_pos=0.45, label_offset=(0, 0.16))
draw_arrow(ax, 3.65, 3.9, 2.2, 4.75, "OTP / Digital Card", label_pos=0.55, label_offset=(0, -0.16))

draw_arrow(ax, 2.2, 2.25, 3.65, 2.9, "Admin Credentials", label_pos=0.45, label_offset=(0, 0.16))
draw_arrow(ax, 3.65, 2.6, 2.2, 1.9, "Verification & Reports", label_pos=0.55, label_offset=(0, -0.16))

draw_arrow(ax, 7.8, 5.15, 6.35, 4.3, "Emergency Requests", label_pos=0.45, label_offset=(0, 0.16))
draw_arrow(ax, 6.35, 3.9, 7.8, 4.75, "Matched Donors", label_pos=0.55, label_offset=(0, -0.16))

draw_arrow(ax, 6.35, 2.8, 7.8, 2.1, "Alert Notifications", label_pos=0.5, label_offset=(0, 0.16))

fig.tight_layout()
fig.savefig(os.path.join(out_dir, "Figure_7.1_Level_0_DFD.png"), dpi=300, bbox_inches='tight', facecolor='white')
plt.close(fig)


# ==========================================================
# 2. GENERATE FIGURE 7.2: LEVEL 1 DFD (ORGAN DONATION VERSION)
# ==========================================================
fig, ax = plt.subplots(figsize=(9, 6.5), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 7.2)
ax.axis('off')

# Section Heading & Caption
ax.text(0.7, 6.7, "Level 1", fontsize=14, fontweight='bold')
ax.text(5.0, 0.4, "Figure 7.2 Level 1 data flow diagram", fontsize=12.5, fontweight='bold', fontstyle='italic', ha='center')

# Entities on the left
draw_entity(ax, 0.8, 4.3, 1.5, 0.7, "USER", fontsize=10)
draw_entity(ax, 0.8, 1.7, 1.5, 0.7, "ADMIN", fontsize=10)

# Process 1.0 (Registration Process)
draw_split_circle(ax, 3.8, 3.8, 1.05, 0.85, "1.0", ["REGISTRATION", "PROCESS"], fontsize=8.8)

# Datastore (USER/ADMIN DATA)
draw_datastore(ax, 3.8, 1.2, 2.2, 0.65, "USER/ADMIN DATA", fontsize=8.5)

# Process 2.0 (Login Process)
draw_split_circle(ax, 6.3, 3.8, 0.95, 0.8, "2.0", ["LOGIN", "PROCESS"], fontsize=8.8)

# Process 3.0 (Organ Donation Management)
draw_split_circle(ax, 8.3, 5.5, 1.05, 0.85, "3.0", ["ORGAN DONATION", "MANAGEMENT"], fontsize=8.2)

# Process 4.0 (Receiver & Matching Management)
draw_split_circle(ax, 8.3, 2.0, 1.05, 0.85, "4.0", ["RECEIVER & MATCH", "MANAGEMENT"], fontsize=8.2)

# Connections & Arrows
draw_arrow(ax, 2.3, 4.65, 2.85, 4.05) # USER -> 1.0
draw_arrow(ax, 2.3, 2.05, 2.9, 3.35)  # ADMIN -> 1.0
draw_arrow(ax, 3.8, 2.95, 3.8, 1.55)  # 1.0 -> USER/ADMIN DATA
draw_arrow(ax, 4.85, 3.8, 5.35, 3.8)  # 1.0 -> 2.0
draw_arrow(ax, 7.05, 4.3, 7.55, 4.95) # 2.0 -> 3.0
draw_arrow(ax, 7.0, 3.3, 7.55, 2.55)  # 2.0 -> 4.0

fig.tight_layout()
fig.savefig(os.path.join(out_dir, "Figure_7.2_Level_1_DFD.png"), dpi=300, bbox_inches='tight', facecolor='white')
plt.close(fig)


# ==========================================================
# 2B. GENERATE FIGURE 7.2 SAMPLE (ORDERING / CUSTOMER MANAGEMENT)
# ==========================================================
fig, ax = plt.subplots(figsize=(9, 6.5), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 7.2)
ax.axis('off')

ax.text(0.7, 6.7, "Level 1", fontsize=14, fontweight='bold')
ax.text(5.0, 0.4, "Figure 7.2 Level 1 data flow diagram", fontsize=12.5, fontweight='bold', fontstyle='italic', ha='center')

draw_entity(ax, 0.8, 4.3, 1.5, 0.7, "USER", fontsize=10)
draw_entity(ax, 0.8, 1.7, 1.5, 0.7, "ADMIN", fontsize=10)

draw_split_circle(ax, 3.8, 3.8, 1.05, 0.85, "1.0", ["REGISTRATION", "PROCESS"], fontsize=8.8)
draw_datastore(ax, 3.8, 1.2, 2.2, 0.65, "USER/ADMIN DATA", fontsize=8.5)
draw_split_circle(ax, 6.3, 3.8, 0.95, 0.8, "2.0", ["LOGIN", "PROCESS"], fontsize=8.8)
draw_split_circle(ax, 8.3, 5.5, 1.05, 0.85, "3.0", ["ORDERING", "MANAGEMENT"], fontsize=8.5)
draw_split_circle(ax, 8.3, 2.0, 1.05, 0.85, "4.0", ["CUSTOMER", "MANAGEMENT"], fontsize=8.5)

draw_arrow(ax, 2.3, 4.65, 2.85, 4.05)
draw_arrow(ax, 2.3, 2.05, 2.9, 3.35)
draw_arrow(ax, 3.8, 2.95, 3.8, 1.55)
draw_arrow(ax, 4.85, 3.8, 5.35, 3.8)
draw_arrow(ax, 7.05, 4.3, 7.55, 4.95)
draw_arrow(ax, 7.0, 3.3, 7.55, 2.55)

fig.tight_layout()
fig.savefig(os.path.join(out_dir, "Figure_7.2_Level_1_DFD_Sample.png"), dpi=300, bbox_inches='tight', facecolor='white')
plt.close(fig)


# ==========================================================
# 3. GENERATE FIGURE 7.3: LEVEL 2 DFD (DETAILED SUB-PROCESSES)
# ==========================================================
fig, ax = plt.subplots(figsize=(9, 6.5), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 7.2)
ax.axis('off')

# Heading & Caption
ax.text(0.7, 6.7, "Level 2", fontsize=14, fontweight='bold')
ax.text(5.0, 0.4, "Figure 7.3 Level 2 data flow diagram", fontsize=12.5, fontweight='bold', fontstyle='italic', ha='center')

# Entities
draw_entity(ax, 0.5, 4.9, 1.4, 0.65, "DONOR", fontsize=9.5)
draw_entity(ax, 0.5, 1.6, 1.4, 0.65, "RECEIVER", fontsize=9.5)

# Sub-Processes
draw_split_circle(ax, 2.8, 5.2, 0.8, 0.65, "3.1", ["INPUT & OTP", "VERIFY"], fontsize=8)
draw_split_circle(ax, 5.3, 5.2, 0.8, 0.65, "3.2", ["STORE DONOR", "PROFILE"], fontsize=8)
draw_split_circle(ax, 8.0, 5.2, 0.88, 0.65, "3.3", ["GENERATE CARD", "& QR CODE"], fontsize=8)

# Data Stores
draw_datastore(ax, 5.3, 3.6, 2.3, 0.55, "DONORS STORE (D3)", fontsize=8)
draw_datastore(ax, 5.3, 2.6, 2.3, 0.55, "RECEIVERS STORE (D5)", fontsize=8)

draw_split_circle(ax, 2.8, 1.9, 0.8, 0.65, "4.1", ["PATIENT REG &", "UPLOADS"], fontsize=8)
draw_split_circle(ax, 8.0, 1.9, 0.9, 0.65, "4.2", ["AI COMPATIBILITY", "& MATCHING"], fontsize=8)

# Arrows
draw_arrow(ax, 1.9, 5.2, 2.0, 5.2)
draw_arrow(ax, 3.6, 5.2, 4.5, 5.2)
draw_arrow(ax, 6.1, 5.2, 7.12, 5.2)
draw_arrow(ax, 5.3, 4.55, 5.3, 3.9) # 3.2 -> Donors Store

draw_arrow(ax, 1.9, 1.9, 2.0, 1.9)
draw_arrow(ax, 3.6, 2.15, 4.3, 2.5) # 4.1 -> Receivers Store

draw_arrow(ax, 6.45, 3.7, 7.25, 2.45) # Donors Store -> 4.2 Match
draw_arrow(ax, 6.45, 2.7, 7.2, 2.1)   # Receivers Store -> 4.2 Match

# Return card
ax.annotate(
    '', xy=(1.2, 5.55), xytext=(8.0, 5.85),
    arrowprops=dict(facecolor='black', edgecolor='black', arrowstyle='->', lw=1.4,
                    connectionstyle="arc3,rad=-0.22"),
    zorder=1
)
ax.text(4.6, 6.35, "Download Digital PDF Card & QR Code", ha='center', va='center', fontsize=8.5, fontstyle='italic')

fig.tight_layout()
fig.savefig(os.path.join(out_dir, "Figure_7.3_Level_2_DFD.png"), dpi=300, bbox_inches='tight', facecolor='white')
plt.close(fig)

print("Regenerated all images with perfect spacing!")

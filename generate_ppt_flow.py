import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch

# Standard 16:9 widescreen presentation canvas (16 x 9.2 inches, 300 DPI)
fig = plt.figure(figsize=(16, 9.2), dpi=300)
ax = plt.gca()
ax.set_xlim(0, 16.4)
ax.set_ylim(0, 9.2)
ax.axis('off')

# Clean modern background
fig.patch.set_facecolor('#F8FAFC')
ax.set_facecolor('#F8FAFC')

# Header Title & Subtitle
plt.text(8.2, 8.65, "ORGAN & BLOOD DONATION MANAGEMENT SYSTEM (ODMS)", 
         ha='center', va='center', fontsize=21, fontweight='bold', color='#0F172A', fontfamily='sans-serif')
plt.text(8.2, 8.22, "System Architecture & End-to-End Workflow for Project Viva & Presentation", 
         ha='center', va='center', fontsize=12, color='#64748B', fontfamily='sans-serif')

# Section Labels (Left Side)
def draw_track_badge(x, y, w, h, text, bg_color):
    badge = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.12",
                           facecolor=bg_color, edgecolor='none', zorder=2)
    ax.add_patch(badge)
    ax.text(x + w/2, y + h/2, text, color='#FFFFFF', fontsize=9.5, fontweight='bold',
            ha='center', va='center', zorder=3, fontfamily='sans-serif')

draw_track_badge(0.7, 7.55, 3.2, 0.42, "TRACK 1: DONOR LIFECYCLE", "#1D4ED8")
draw_track_badge(0.7, 3.75, 3.2, 0.42, "TRACK 2: RECEIVER & MATCHING", "#B91C1C")

# Helper to draw cards
def draw_card(x, y, w, h, bg_color, border_color, title, subtitle_list, badge=None, badge_bg="#0F172A"):
    # Drop shadow
    shadow = FancyBboxPatch((x+0.05, y-0.05), w, h, boxstyle="round,pad=0.08,rounding_size=0.14",
                            facecolor='#E2E8F0', edgecolor='none', zorder=2)
    ax.add_patch(shadow)
    
    # Main Box
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.14",
                         facecolor=bg_color, edgecolor=border_color, linewidth=2, zorder=3)
    ax.add_patch(box)
    
    # Badge (e.g. Step number)
    if badge:
        badge_box = FancyBboxPatch((x+0.16, y+h-0.34), 0.72, 0.26, boxstyle="round,pad=0.03,rounding_size=0.08",
                                   facecolor=badge_bg, edgecolor='none', zorder=4)
        ax.add_patch(badge_box)
        ax.text(x+0.52, y+h-0.21, badge, color='#FFFFFF', fontsize=8, fontweight='bold',
                ha='center', va='center', zorder=5, fontfamily='sans-serif')
    
    # Title
    title_x = x + (1.05 if badge else w/2)
    title_ha = 'left' if badge else 'center'
    ax.text(title_x, y+h-0.21, title, color='#0F172A', fontsize=10.8, fontweight='bold',
            ha=title_ha, va='center', zorder=4, fontfamily='sans-serif')
    
    # Subtle separator line
    ax.plot([x+0.15, x+w-0.15], [y+h-0.45, y+h-0.45], color=border_color, linewidth=1, alpha=0.8, zorder=4)
    
    # Subtitle / content bullet points
    start_y = y + h - 0.78
    for item in subtitle_list:
        ax.text(x+0.2, start_y, f"• {item}", color='#334155', fontsize=8.6,
                ha='left', va='center', zorder=4, fontfamily='sans-serif')
        start_y -= 0.33

# Connector Arrow Helper
def draw_connector(x1, y1, x2, y2, label=None, label_pos=0.5, label_offset=(0, 0.18), color='#2563EB', lw=2.2):
    ax.annotate(
        '', xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle="->,head_width=0.35,head_length=0.45", 
                        color=color, lw=lw),
        zorder=6
    )
    if label:
        lx = x1 + (x2 - x1) * label_pos + label_offset[0]
        ly = y1 + (y2 - y1) * label_pos + label_offset[1]
        ax.text(lx, ly, label, ha='center', va='center', fontsize=8.2, fontweight='bold', color=color,
                bbox=dict(boxstyle='round,pad=0.25', fc='#FFFFFF', ec=color, lw=1.2, alpha=0.98), zorder=7, fontfamily='sans-serif')

CARD_W = 2.85
CARD_H = 2.45
ROW1_Y = 4.85
ROW2_Y = 1.05

X1 = 0.7
X2 = 4.65
X3 = 8.6
X4 = 12.55

# ==========================================
# ROW 1 (TOP): DONOR LIFECYCLE
# ==========================================
# Box 1A: Donor Registration
draw_card(X1, ROW1_Y, CARD_W, CARD_H, '#EFF6FF', '#93C5FD', "DONOR REGISTRATION", 
          ["Organ & Blood Donor Forms",
           "Age 18+ Prerequisite Check",
           "Organ Checklist (Heart, Kidney..)",
           "Photo & Medical History",
           "City Autocomplete Suggestion"],
          badge="STEP 1", badge_bg="#2563EB")

# Box 1B: OTP Verification
draw_card(X2, ROW1_Y, CARD_W, CARD_H, '#FAF5FF', '#D8B4FE', "OTP AUTHENTICATION", 
          ["6-Digit Mobile Verification",
           "Twilio / Fast2SMS Gateway",
           "Strict Form Prerequisite Check",
           "Tamper-Proof Mobile Validation",
           "Prevents Fake / Bot Entries"],
          badge="STEP 2", badge_bg="#7C3AED")

# Box 1C: Central Database
draw_card(X3, ROW1_Y, CARD_W, CARD_H, '#F0FDF4', '#86EFAC', "DATABASE ENGINE", 
          ["MySQL Relational DB",
           "Password Hashing (PBKDF2)",
           "Active Donor Pool Records",
           "Blood Stock Status Registry",
           "Secure File & Photo Storage"],
          badge="STEP 3", badge_bg="#16A34A")

# Box 1D: Digital Donor Card
draw_card(X4, ROW1_Y, CARD_W, CARD_H, '#ECFDF5', '#6EE7B7', "DIGITAL DONOR CARD", 
          ["ReportLab Automated PDF Card",
           "Encrypted QR Code Verification",
           "Instant Public QR Page Link",
           "Automated SMTP Email Dispatch",
           "Official Government Standard ID"],
          badge="STEP 4", badge_bg="#059669")

# Row 1 Arrows
draw_connector(X1 + CARD_W, ROW1_Y + CARD_H/2, X2, ROW1_Y + CARD_H/2, label="1. Send OTP", color='#2563EB')
draw_connector(X2 + CARD_W, ROW1_Y + CARD_H/2, X3, ROW1_Y + CARD_H/2, label="2. Verify & Save", color='#7C3AED')
draw_connector(X3 + CARD_W, ROW1_Y + CARD_H/2, X4, ROW1_Y + CARD_H/2, label="3. Issue Card & QR", color='#059669')

# ==========================================
# ROW 2 (BOTTOM): RECEIVER & MATCHING
# ==========================================
# Box 2A: Receiver / Urgent Request
draw_card(X1, ROW2_Y, CARD_W, CARD_H, '#FEF2F2', '#FCA5A5', "RECEIVER REQUEST", 
          ["Patient Organ / Blood Request",
           "Emergency Level (1 to 4)",
           "Hospital Details & City",
           "Urgent Blood Need Portal",
           "Real-Time Bed/Transfusion Need"],
          badge="STEP 1", badge_bg="#DC2626")

# Box 2B: Medical Reports Upload
draw_card(X2, ROW2_Y, CARD_W, CARD_H, '#FFF1F2', '#FDA4AF', "MEDICAL VERIFICATION", 
          ["Upload Medical Reports (16MB)",
           "Blood Test & Compatibility Report",
           "ECG & Organ Function Scans",
           "Doctor / Hospital Certificate",
           "Clinical Data Integrity Check"],
          badge="STEP 2", badge_bg="#E11D48")

# Box 2C: AI Matching Engine
draw_card(X3, ROW2_Y, CARD_W, CARD_H, '#FFFBEB', '#FCD34D', "AI MATCHING ENGINE", 
          ["ABO/Rh Compatibility (35%)",
           "Geographic Proximity / GPS (20%)",
           "Medical Urgency Score (20%)",
           "Donor Availability & Recency (25%)",
           "Weighted Compatibility Score (0-100)"],
          badge="STEP 3", badge_bg="#D97706")

# Box 2D: Admin Portal & Dispatch
draw_card(X4, ROW2_Y, CARD_W, CARD_H, '#EFF6FF', '#60A5FA', "ADMIN DISPATCH & ALERT", 
          ["2FA Secured Admin Approval",
           "Review Ranked Match Candidates",
           "Instant Email / SMS Hospital Alert",
           "Organ Transplant Coordination",
           "Real-Time Notification Center"],
          badge="STEP 4", badge_bg="#2563EB")

# Row 2 Arrows
draw_connector(X1 + CARD_W, ROW2_Y + CARD_H/2, X2, ROW2_Y + CARD_H/2, label="1. Attach Docs", color='#DC2626')
draw_connector(X2 + CARD_W, ROW2_Y + CARD_H/2, X3, ROW2_Y + CARD_H/2, label="2. Request Match", color='#E11D48')
draw_connector(X3 + CARD_W, ROW2_Y + CARD_H/2, X4, ROW2_Y + CARD_H/2, label="3. Rank & Alert", color='#D97706')

# Vertical Arrow: Database (Row 1) feeds into AI Matching Engine (Row 2)
draw_connector(X3 + CARD_W/2, ROW1_Y, X3 + CARD_W/2, ROW2_Y + CARD_H, 
               label="Live Verified Donor Pool", label_offset=(1.15, 0), color='#16A34A', lw=2.4)

# Footer Technology Bar
footer_box = FancyBboxPatch((0.7, 0.30), 14.7, 0.45, boxstyle="round,pad=0.05,rounding_size=0.1",
                            facecolor='#F1F5F9', edgecolor='#CBD5E1', linewidth=1, zorder=2)
ax.add_patch(footer_box)
plt.text(8.05, 0.52, "Core Tech Stack: Python Flask (REST API) | MySQL Database | ReportLab PDF Engine | QR Code Generator | AI Matching Matrix", 
         ha='center', va='center', fontsize=9.8, fontweight='bold', color='#475569', fontfamily='sans-serif')

out_path = r"c:\xampp1\htdocs\Organ Donation\ppt_flow_diagram.png"
plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
plt.close()
print(f"Perfect diagram generated at: {out_path}")

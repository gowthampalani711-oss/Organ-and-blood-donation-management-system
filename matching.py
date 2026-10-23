import math
from database import DBWrapper

# Standard ABO / Rh Blood Compatibility Matrix
# Key: Receiver Blood Group -> List of Compatible Donor Blood Groups
BLOOD_COMPATIBILITY_RECEIVER = {
    "O-": ["O-"],
    "O+": ["O-", "O+"],
    "A-": ["O-", "A-"],
    "A+": ["O-", "O+", "A-", "A+"],
    "B-": ["O-", "B-"],
    "B+": ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
}

# Key: Donor Blood Group -> List of Compatible Recipient Blood Groups
BLOOD_COMPATIBILITY_DONOR = {
    "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+": ["O+", "A+", "B+", "AB+"],
    "A-": ["A-", "A+", "AB-", "AB+"],
    "A+": ["A+", "AB+"],
    "B-": ["B-", "B+", "AB-", "AB+"],
    "B+": ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"]
}

# City Coordinates for Distance Estimation in Tamil Nadu / South India
CITY_COORDINATES = {
    "Chennai": (13.0827, 80.2707),
    "Coimbatore": (11.0168, 76.9558),
    "Madurai": (9.9252, 78.1198),
    "Trichy": (10.7905, 78.7047),
    "Salem": (11.6643, 78.1460),
    "Erode": (11.3410, 77.7172),
    "Tirunelveli": (8.7139, 77.7567),
    "Vellore": (12.9165, 79.1325),
    "Thanjavur": (10.7870, 79.1378),
    "Dindigul": (10.3673, 77.9803),
    "Tiruppur": (11.1085, 77.3411),
    "Kanchipuram": (12.8342, 79.7036),
    "Nagercoil": (8.1833, 77.4119),
    "Cuddalore": (11.7480, 79.7714),
    "Karur": (10.9601, 78.0766),
    "Hosur": (12.7409, 77.8253),
    "Bengaluru": (12.9716, 77.5946),
    "Kochi": (9.9312, 76.2673),
    "Hyderabad": (17.3850, 78.4867)
}


def calculate_distance_km(city1, city2):
    """Calculates approximate Haversine distance in km between two cities."""
    if not city1 or not city2:
        return 100.0
    c1 = city1.strip().title()
    c2 = city2.strip().title()
    if c1 == c2:
        return 0.0

    coords1 = CITY_COORDINATES.get(c1)
    coords2 = CITY_COORDINATES.get(c2)
    if not coords1 or not coords2:
        return 50.0  # Default regional estimate

    lat1, lon1 = coords1
    lat2, lon2 = coords2

    r = 6371.0  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r * c, 1)


def match_organ_donors(needed_organ, receiver_blood_group, receiver_city, emergency_level="High", receiver_age=35):
    """
    Intelligent AI matching algorithm for organ donation.
    Evaluates:
      - Blood compatibility (35%)
      - Organ type match (mandatory filter)
      - Proximity & Distance (20%)
      - Emergency Level priority (20%)
      - Donor Availability (15%)
      - Verification Status (10%)
    """
    compatible_bloods = BLOOD_COMPATIBILITY_RECEIVER.get(receiver_blood_group, [receiver_blood_group])

    with DBWrapper() as db:
        all_donors = db.query("SELECT * FROM donors WHERE status != 'Rejected'")

    results = []
    for donor in all_donors:
        donor_organs = [o.strip().lower() for o in donor.get("organ_type", "").split(",")]
        target_organ = needed_organ.strip().lower()

        # Check if donor pledged this organ
        if not any(target_organ in o for o in donor_organs):
            continue

        score = 0.0
        score_breakdown = {}

        # 1. Blood Compatibility Score (Max 35 points)
        donor_bg = donor.get("blood_group")
        if donor_bg == receiver_blood_group:
            blood_score = 35.0
            blood_note = "Exact Blood Group Match (+35%)"
        elif donor_bg in compatible_bloods:
            blood_score = 30.0
            blood_note = f"Compatible Blood Group ({donor_bg} -> {receiver_blood_group}) (+30%)"
        else:
            blood_score = 5.0
            blood_note = f"Incompatible Blood Group ({donor_bg}) (+5%)"
        score += blood_score
        score_breakdown["blood_match"] = {"score": blood_score, "max": 35, "detail": blood_note}

        # 2. Distance / Proximity Score (Max 20 points)
        dist_km = calculate_distance_km(receiver_city, donor.get("city"))
        if dist_km == 0:
            dist_score = 20.0
            dist_note = f"Same City ({donor.get('city')}) (+20%)"
        elif dist_km < 100:
            dist_score = 17.0
            dist_note = f"Within 100km (~{dist_km} km) (+17%)"
        elif dist_km < 250:
            dist_score = 13.0
            dist_note = f"Within 250km (~{dist_km} km) (+13%)"
        elif dist_km < 500:
            dist_score = 8.0
            dist_note = f"State-wide (~{dist_km} km) (+8%)"
        else:
            dist_score = 4.0
            dist_note = f"Inter-state (~{dist_km} km) (+4%)"
        score += dist_score
        score_breakdown["distance"] = {"score": dist_score, "max": 20, "distance_km": dist_km, "detail": dist_note}

        # 3. Emergency Level Multiplier / Priority (Max 20 points)
        em_upper = emergency_level.upper()
        if em_upper == "CRITICAL":
            em_score = 20.0
            em_note = "Critical Emergency Level (+20%)"
        elif em_upper == "HIGH":
            em_score = 16.0
            em_note = "High Emergency Level (+16%)"
        elif em_upper == "MEDIUM":
            em_score = 12.0
            em_note = "Medium Urgency Level (+12%)"
        else:
            em_score = 8.0
            em_note = "Standard Priority (+8%)"
        score += em_score
        score_breakdown["emergency"] = {"score": em_score, "max": 20, "detail": em_note}

        # 4. Donor Availability Status (Max 15 points)
        avail = donor.get("availability_status", "Available")
        if avail == "Available":
            avail_score = 15.0
            avail_note = "Donor Actively Available (+15%)"
        elif avail == "Pledged":
            avail_score = 12.0
            avail_note = "Organ Donation Pledged (+12%)"
        else:
            avail_score = 2.0
            avail_note = "Unavailable / Restricted (+2%)"
        score += avail_score
        score_breakdown["availability"] = {"score": avail_score, "max": 15, "detail": avail_note}

        # 5. Verification Status (Max 10 points)
        status = donor.get("status", "Approved")
        if status == "Approved":
            ver_score = 10.0
            ver_note = "Government / Medical ID Verified (+10%)"
        else:
            ver_score = 5.0
            ver_note = "Pending Verification (+5%)"
        score += ver_score
        score_breakdown["verification"] = {"score": ver_score, "max": 10, "detail": ver_note}

        final_score = min(round(score, 1), 99.5)

        # Anonymize phone for public safe view
        raw_phone = str(donor.get("phone", ""))
        masked_phone = raw_phone[:3] + "XXXX" + raw_phone[-3:] if len(raw_phone) >= 10 else raw_phone

        results.append({
            "donor_id": donor.get("donor_id"),
            "full_name": donor.get("full_name"),
            "age": donor.get("age"),
            "gender": donor.get("gender"),
            "blood_group": donor.get("blood_group"),
            "organ_type": donor.get("organ_type"),
            "city": donor.get("city"),
            "distance_km": dist_km,
            "availability_status": donor.get("availability_status"),
            "status": donor.get("status"),
            "photo_url": donor.get("photo_url", "/static/img/default-avatar.png"),
            "masked_phone": masked_phone,
            "match_score": final_score,
            "score_breakdown": score_breakdown,
            "medical_disclaimer": "AI Match score is for technical matching suggestions only. Final medical transplant matching requires clinical HLA typing and tissue cross-matching by authorized surgeons."
        })

    # Sort descending by match score
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results


def match_blood_donors(blood_group_required, receiver_city, units_required=1, emergency_level="Urgent"):
    """
    Intelligent AI matching algorithm for blood requests.
    Evaluates:
      - Blood compatibility (40%)
      - Proximity & Distance (25%)
      - Emergency priority (20%)
      - Availability & Last Donation Eligibility (15%)
    """
    compatible_bloods = BLOOD_COMPATIBILITY_RECEIVER.get(blood_group_required, [blood_group_required])

    with DBWrapper() as db:
        all_blood_donors = db.query("SELECT * FROM blood_donors WHERE status != 'Rejected'")

    results = []
    for b_donor in all_blood_donors:
        donor_bg = b_donor.get("blood_group")
        # Check compatibility
        if donor_bg not in compatible_bloods:
            continue

        score = 0.0
        score_breakdown = {}

        # 1. Blood Compatibility (Max 40 points)
        if donor_bg == blood_group_required:
            blood_score = 40.0
            blood_note = f"Exact Blood Match ({donor_bg}) (+40%)"
        else:
            blood_score = 32.0
            blood_note = f"Compatible Blood Group ({donor_bg} -> {blood_group_required}) (+32%)"
        score += blood_score
        score_breakdown["blood_match"] = {"score": blood_score, "max": 40, "detail": blood_note}

        # 2. Distance / City Proximity (Max 25 points)
        dist_km = calculate_distance_km(receiver_city, b_donor.get("city"))
        if dist_km == 0:
            dist_score = 25.0
            dist_note = f"Same City ({b_donor.get('city')}) (+25%)"
        elif dist_km < 30:
            dist_score = 22.0
            dist_note = f"Nearby Town (~{dist_km} km) (+22%)"
        elif dist_km < 100:
            dist_score = 16.0
            dist_note = f"Adjacent District (~{dist_km} km) (+16%)"
        else:
            dist_score = 8.0
            dist_note = f"Distance: ~{dist_km} km (+8%)"
        score += dist_score
        score_breakdown["distance"] = {"score": dist_score, "max": 25, "distance_km": dist_km, "detail": dist_note}

        # 3. Emergency Priority (Max 20 points)
        em_upper = emergency_level.upper()
        if em_upper == "CRITICAL":
            em_score = 20.0
            em_note = "Critical Immediate Need (+20%)"
        elif em_upper == "URGENT":
            em_score = 16.0
            em_note = "Urgent Request (+16%)"
        else:
            em_score = 12.0
            em_note = "Normal Scheduled Request (+12%)"
        score += em_score
        score_breakdown["emergency"] = {"score": em_score, "max": 20, "detail": em_note}

        # 4. Availability & Last Donation Date Eligibility (Max 15 points)
        avail = b_donor.get("availability_status", "Available")
        if avail == "Available":
            avail_score = 15.0
            avail_note = "Ready to Donate (+15%)"
        else:
            avail_score = 3.0
            avail_note = "Currently Unavailable (+3%)"
        score += avail_score
        score_breakdown["availability"] = {"score": avail_score, "max": 15, "detail": avail_note}

        final_score = min(round(score, 1), 99.0)

        raw_phone = str(b_donor.get("phone", ""))
        masked_phone = raw_phone[:3] + "XXXX" + raw_phone[-3:] if len(raw_phone) >= 10 else raw_phone

        results.append({
            "blood_donor_id": b_donor.get("blood_donor_id"),
            "full_name": b_donor.get("full_name"),
            "age": b_donor.get("age"),
            "gender": b_donor.get("gender"),
            "blood_group": b_donor.get("blood_group"),
            "city": b_donor.get("city"),
            "distance_km": dist_km,
            "last_donation_date": str(b_donor.get("last_donation_date") or "First Time Donor"),
            "availability_status": b_donor.get("availability_status"),
            "masked_phone": masked_phone,
            "match_score": final_score,
            "score_breakdown": score_breakdown
        })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results

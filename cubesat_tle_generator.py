"""
ISS CubeSat TLE Generator
Generates a TLE for a cubesat deployed from the ISS based on current ISS orbital parameters.
"""

from datetime import datetime, timezone
import math
import requests
import re

def fetch_iss_tle():
    """Fetch current ISS TLE from CelesTrak"""
    url = 'https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        lines = response.text.strip().split('\n')
        if len(lines) >= 3:
            return lines[0].strip(), lines[1].strip(), lines[2].strip()
        else:
            raise ValueError("Invalid TLE format received")
    except Exception as e:
        print(f"Error fetching ISS TLE: {e}")
        # Fallback to example TLE (you'd want to update this manually)
        return ("ISS (ZARYA)",
                "1 25544U 98067A   25283.50000000  .00012345  00000-0  23456-3 0  9999",
                "2 25544  51.6400 123.4567 0001234  45.6789 314.5678 15.50000000123456")

def parse_scientific(s):
    s = s.strip()
    # Match: optional sign, digits, dash or plus, digits
    match = re.match(r'^(-?\d+)([-+])(\d+)$', s)
    if match:
        base, sign, exp = match.groups()
        return float(f'{base}e{sign}{exp}')
    raise ValueError(f"Invalid format: {s}")

def parse_tle_line1(line):
    """Parse TLE line 1"""
    return {
        'catalog_num': int(line[2:7]),
        'classification': line[7],
        'launch_year': int(line[9:11]),
        'launch_num': int(line[11:14]),
        'launch_piece': line[14:17].strip(),
        'epoch_year': int(line[18:20]),
        'epoch_day': float(line[20:32]),
        'mean_motion_dot': float(line[33:43]),
        'mean_motion_ddot': parse_scientific(line[44:52]),
        'bstar': parse_scientific(line[53:61]),
        'ephemeris_type': int(line[62]),
        'element_num': int(line[64:68]),
        'checksum1': int(line[68])
    }

def parse_tle_line2(line):
    """Parse TLE line 2"""
    return {
        'catalog_num': int(line[2:7]),
        'inclination': float(line[8:16]),
        'raan': float(line[17:25]),
        'eccentricity': float('0.' + line[26:33]),
        'arg_perigee': float(line[34:42]),
        'mean_anomaly': float(line[43:51]),
        'mean_motion': float(line[52:63]),
        'rev_number': int(line[63:68]),
        'checksum2': int(line[68])
    }

def calculate_checksum(line):
    """Calculate TLE checksum"""
    checksum = 0
    for char in line[0:68]:
        if char.isdigit():
            checksum += int(char)
        elif char == '-':
            checksum += 1
    return checksum % 10

def format_exponential(value, width=8):
    """Format number in TLE exponential notation"""
    if value == 0:
        return ' ' + '0' * (width - 2) + '-0'
    
    sign = '-' if value < 0 else ' '
    abs_val = abs(value)
    exponent = math.floor(math.log10(abs_val))
    mantissa = abs_val / (10 ** exponent)
    mantissa_str = f"{mantissa:.5f}"[2:]  # Remove "0."
    exp_str = f"{abs(exponent)}"
    exp_sign = '-' if exponent < 0 else '+'
    
    return f"{sign}{mantissa_str}{exp_sign}{exp_str}"

def generate_cubesat_tle(cubesat_name, catalog_num, deployment_date, 
                         altitude_drop_km=0.5, mass_kg=3.0, area_m2=0.01):
    """
    Generate TLE for ISS-deployed cubesat
    
    Parameters:
    - cubesat_name: Name of your cubesat (max 24 chars)
    - catalog_num: Temporary catalog number (99999 or similar)
    - deployment_date: datetime object for deployment (UTC)
    - altitude_drop_km: How much lower than ISS (typically 0.3-1.0 km)
    - mass_kg: Cubesat mass in kg
    - area_m2: Cross-sectional area in m²
    """
    
    # Fetch current ISS TLE
    print("Fetching current ISS TLE...")
    name, line1, line2 = fetch_iss_tle()
    print(line1)
    # Parse ISS TLE
    iss_l1 = parse_tle_line1(line1)
    iss_l2 = parse_tle_line2(line2)
    
    print(f"\nBase ISS orbital parameters:")
    print(f"  Inclination: {iss_l2['inclination']:.4f}°")
    print(f"  RAAN: {iss_l2['raan']:.4f}°")
    print(f"  Eccentricity: {iss_l2['eccentricity']:.7f}")
    print(f"  Arg of Perigee: {iss_l2['arg_perigee']:.4f}°")
    print(f"  Mean Anomaly: {iss_l2['mean_anomaly']:.4f}°")
    print(f"  Mean Motion: {iss_l2['mean_motion']:.8f} rev/day")
    
    # Calculate adjustments for cubesat
    # Lower altitude = higher mean motion
    # Approximate: 1 km lower ≈ 0.05 rev/day increase
    mean_motion_increase = altitude_drop_km * 0.05
    new_mean_motion = iss_l2['mean_motion'] + mean_motion_increase
    
    # Adjust B* (ballistic coefficient) based on mass and area
    # B* = (Cd * A) / (2 * m) where Cd ≈ 2.2 for cubesats
    # ISS B* is typically around 2e-5, cubesats are higher (more drag)
    cd = 2.2
    bstar_cubesat = (cd * area_m2) / (2.0 * mass_kg)
    bstar_formatted = bstar_cubesat * 1e-5  # TLE uses Earth radii^-1
    
    # Convert deployment date to TLE epoch format
    year = deployment_date.year % 100
    day_of_year = deployment_date.timetuple().tm_yday
    hour_frac = (deployment_date.hour + 
                 deployment_date.minute / 60.0 + 
                 deployment_date.second / 3600.0) / 24.0
    epoch_day = day_of_year + hour_frac
    
    # Generate Line 1
    line1_new = f"1 {catalog_num:5d}U 25999A   {year:02d}{epoch_day:012.8f} "
    line1_new += f"{iss_l1['mean_motion_dot']:10.8f} "
    line1_new += " 00000-0 "
    line1_new += format_exponential(bstar_formatted)
    line1_new += f" 0  9999"
    checksum1 = calculate_checksum(line1_new)
    line1_new += str(checksum1)
    
    # Generate Line 2
    # Keep most ISS parameters, adjust mean motion
    line2_new = f"2 {catalog_num:5d} {iss_l2['inclination']:8.4f} "
    line2_new += f"{iss_l2['raan']:8.4f} "
    ecc_str = f"{iss_l2['eccentricity']:.7f}"[2:]  # Remove "0."
    line2_new += f"{ecc_str:7s} "
    line2_new += f"{iss_l2['arg_perigee']:8.4f} "
    line2_new += f"{iss_l2['mean_anomaly']:8.4f} "
    line2_new += f"{new_mean_motion:11.8f}"
    line2_new += f"{0:5d}"  # Rev number at epoch
    checksum2 = calculate_checksum(line2_new)
    line2_new += str(checksum2)
    
    print(f"\nGenerated CubeSat TLE:")
    print(f"  Mean Motion: {new_mean_motion:.8f} rev/day (+{mean_motion_increase:.3f})")
    print(f"  B*: {bstar_formatted:.5e}")
    print(f"  Epoch: {deployment_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    return cubesat_name[:24], line1_new, line2_new


# Example usage
if __name__ == "__main__":
    # Configuration
    CUBESAT_NAME = "MY-CUBESAT-1"
    CATALOG_NUMBER = 99999  # Placeholder until officially cataloged
    
    # Set deployment date (example: 3 weeks from now)
    deployment_date = datetime(2025, 10, 31, 14, 30, 0, tzinfo=timezone.utc)
    
    # CubeSat specifications
    ALTITUDE_DROP = 0.5  # km below ISS
    MASS = 3.0  # kg (3U cubesat typical)
    AREA = 0.01  # m² (10cm x 10cm face)
    
    print("=" * 70)
    print("ISS CubeSat TLE Generator")
    print("=" * 70)
    
    # Generate TLE
    name, line1, line2 = generate_cubesat_tle(
        CUBESAT_NAME,
        CATALOG_NUMBER,
        deployment_date,
        ALTITUDE_DROP,
        MASS,
        AREA
    )
    
    print("\n" + "=" * 70)
    print("GENERATED TLE (copy these 3 lines):")
    print("=" * 70)
    print(name)
    print(line1)
    print(line2)
    print("=" * 70)
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("1. This TLE is based on PREDICTED parameters")
    print("2. Update immediately after deployment with actual telemetry")
    print("3. Share with tracking networks (AMSAT, SatNOGS) for refinement")
    print("4. TLE accuracy degrades quickly - update within 24-48 hours")
    print("5. Contact your launch provider for official orbital parameters")
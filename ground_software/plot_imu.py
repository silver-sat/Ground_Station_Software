#!/usr/bin/env python3
"""
 @author Lee A. Congdon (lee@silversat.org)
 @brief Extract and plot IMU readings (RX, RY, RZ) from telemetry
 
 This program extracts RES GTY records from the database, parses IMU
 readings, and creates a scatter plot showing RX, RY, RZ values over time.
 
"""

import argparse
import sqlite3
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Dict, Optional

DATABASE_PATH = "./instance/radio.db"


def extract_imu_data(db_path: str) -> List[Dict]:
    """
    Extract IMU readings from RES GTY records.
    
    Args:
        db_path: Path to the SQLite database
    
    Returns:
        List of dictionaries containing timestamp and RX, RY, RZ values
    """
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    
    # Query for RES GTY records (checking bytes 3-9)
    query = """
        SELECT timestamp, response 
        FROM responses 
        WHERE CAST(substr(response, 3, 7) AS TEXT) = 'RES GTY'
        ORDER BY timestamp ASC
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    connection.close()
    
    imu_data = []
    
    for row in rows:
        timestamp_str = row["timestamp"]
        try:
            # Decode response (skip first 2 and last byte for KISS framing)
            response_text = row["response"][2:-1].decode('utf-8', errors='replace')
        except Exception as e:
            print(f"Warning: Could not decode response at {timestamp_str}: {e}")
            continue
        
        # Parse IMU values from response
        parsed = parse_imu_values(response_text)
        
        if parsed:
            try:
                # Parse ISO timestamp
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                imu_data.append({
                    'timestamp': dt,
                    'rx': parsed['rx'],
                    'ry': parsed['ry'],
                    'rz': parsed['rz']
                })
            except ValueError as e:
                print(f"Warning: Could not parse timestamp {timestamp_str}: {e}")
                continue
    
    return imu_data


def parse_imu_values(response_text: str) -> Optional[Dict[str, float]]:
    """
    Parse IMU values (RX, RY, RZ) from telemetry response.
    
    Expected format after 'RES GTY': space-separated tuples like 'RX -0.123'
    
    Args:
        response_text: Decoded response text
    
    Returns:
        Dictionary with 'rx', 'ry', 'rz' keys, or None if parsing fails
    """
    # Pattern to match tuples: 1-2 letter code followed by optional sign and number
    # Example: 'RX -0.123', 'RY 1.456', 'RZ -2.789'
    pattern = r'([A-Z]{1,2})\s+([-+]?\d+\.?\d*)'
    
    matches = re.findall(pattern, response_text)
    
    values = {}
    for code, value_str in matches:
        try:
            values[code.lower()] = float(value_str)
        except ValueError:
            continue
    
    # Check if we have all three IMU readings
    if 'rx' in values and 'ry' in values and 'rz' in values:
        return {
            'rx': values['rx'],
            'ry': values['ry'],
            'rz': values['rz']
        }
    
    return None


def plot_imu_data(data: List[Dict], output_file: str = None):
    """
    Create a scatter plot of IMU readings over time.
    
    Args:
        data: List of dictionaries with timestamp, rx, ry, rz
        output_file: Optional filename to save plot (if None, displays interactively)
    """
    if not data:
        print("No data to plot")
        return
    
    # Extract data for plotting
    timestamps = [d['timestamp'] for d in data]
    rx_values = [d['rx'] for d in data]
    ry_values = [d['ry'] for d in data]
    rz_values = [d['rz'] for d in data]
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot each axis
    ax.scatter(timestamps, rx_values, label='RX', alpha=0.6, s=30, marker='o')
    ax.scatter(timestamps, ry_values, label='RY', alpha=0.6, s=30, marker='s')
    ax.scatter(timestamps, rz_values, label='RZ', alpha=0.6, s=30, marker='^')
    
    # Format the plot
    ax.set_xlabel('Timestamp', fontsize=12)
    ax.set_ylabel('IMU Reading', fontsize=12)
    ax.set_title('IMU Readings (RX, RY, RZ) Over Time', fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    
    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate()
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Extract and plot IMU readings from telemetry data"
    )
    
    parser.add_argument(
        "--database",
        default=DATABASE_PATH,
        help=f"Path to SQLite database (default: {DATABASE_PATH})"
    )
    
    parser.add_argument(
        "--output",
        help="Output filename for plot (e.g., magnetometer.png). If not specified, displays interactively."
    )
    
    args = parser.parse_args()
    
    print(f"Extracting IMU data from {args.database}...")
    data = extract_imu_data(args.database)
    
    if not data:
        print("No IMU data found in database")
        return
    
    print(f"Found {len(data)} IMU readings")
    print(f"Time range: {data[0]['timestamp']} to {data[-1]['timestamp']}")
    
    # Display sample data
    print("\nSample readings:")
    for i, reading in enumerate(data[:3]):
        print(f"  {reading['timestamp']}: RX={reading['rx']:.3f}, RY={reading['ry']:.3f}, RZ={reading['rz']:.3f}")
    if len(data) > 3:
        print(f"  ... and {len(data) - 3} more")
    
    print("\nGenerating plot...")
    plot_imu_data(data, args.output)


if __name__ == "__main__":
    main()

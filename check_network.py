#!/usr/bin/env python
"""
Network Check Tool
==================
Run this before starting the bot to check if your network allows LinkedIn submissions.

Usage:
    python check_network.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.network_check import run_full_security_check, print_security_report
from modules.proxy_bypass import get_mobile_hotspot_instructions, detect_mobile_hotspot


def main():
    print("\n" + "="*70)
    print("   🔍 LINKEDIN JOB BOT - NETWORK COMPATIBILITY CHECK")
    print("="*70)
    
    # Run security check
    print("\nAnalyzing network configuration...")
    results = run_full_security_check()
    
    # Print report
    print_security_report(results)
    
    # If issues found, show bypass instructions
    if not results["can_submit_applications"]:
        print("\n" + "-"*70)
        print("   💡 HOW TO FIX THIS")
        print("-"*70)
        
        # Check if mobile hotspot is available
        hotspot_available, hotspot_name = detect_mobile_hotspot()
        
        if hotspot_available:
            print(f"\n✅ GOOD NEWS! Mobile hotspot detected: '{hotspot_name}'")
            print("   Simply connect to it and run the bot!")
        else:
            print(get_mobile_hotspot_instructions())
        
        print("\n" + "="*70)
        print("   After connecting to mobile hotspot, run this check again")
        print("   to verify the network is now safe.")
        print("="*70)
    else:
        print("\n✅ Your network is SAFE for LinkedIn applications!")
        print("   You can run the bot normally: python run_dashboard.py")
    
    print()
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()

"""
Proxy Bypass Module for Corporate Networks
Allows routing traffic through SOCKS proxy or mobile hotspot to bypass DLP/SSL inspection.
"""

import socket
import subprocess
import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


def detect_mobile_hotspot() -> Tuple[bool, Optional[str]]:
    """
    Detect if a mobile hotspot network is available.
    
    Returns:
        Tuple of (is_available, network_name)
    """
    try:
        # Get list of available WiFi networks
        result = subprocess.run(
            ["netsh", "wlan", "show", "networks"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            # Common mobile hotspot patterns
            hotspot_patterns = [
                "iphone", "android", "pixel", "galaxy", 
                "oneplus", "hotspot", "mobile", "phone",
                "personal", "portable", "mi ", "redmi",
                "samsung", "huawei", "oppo", "vivo"
            ]
            
            networks = result.stdout.lower()
            for pattern in hotspot_patterns:
                if pattern in networks:
                    # Extract network name
                    for line in result.stdout.split('\n'):
                        if 'SSID' in line and ':' in line:
                            ssid = line.split(':', 1)[1].strip()
                            if pattern in ssid.lower():
                                return True, ssid
            
        return False, None
        
    except Exception as e:
        logger.warning(f"Could not detect mobile hotspot: {e}")
        return False, None


def get_current_network_adapter() -> Dict:
    """Get information about the current network connection."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway } | Select-Object -First 1 InterfaceAlias, IPv4Address, IPv4DefaultGateway | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            import json
            return json.loads(result.stdout)
            
    except Exception as e:
        logger.warning(f"Could not get network adapter info: {e}")
    
    return {}


def test_proxy_connection(proxy_host: str, proxy_port: int, proxy_type: str = "socks5") -> bool:
    """
    Test if a SOCKS proxy is reachable and working.
    
    Args:
        proxy_host: Proxy server hostname or IP
        proxy_port: Proxy server port
        proxy_type: Type of proxy (socks5, socks4, http)
    
    Returns:
        True if proxy is working
    """
    try:
        import socks
        
        # Create a socket with proxy
        s = socks.socksocket()
        
        if proxy_type == "socks5":
            s.set_proxy(socks.SOCKS5, proxy_host, proxy_port)
        elif proxy_type == "socks4":
            s.set_proxy(socks.SOCKS4, proxy_host, proxy_port)
        else:
            s.set_proxy(socks.HTTP, proxy_host, proxy_port)
        
        s.settimeout(10)
        s.connect(("www.linkedin.com", 443))
        s.close()
        return True
        
    except ImportError:
        logger.warning("PySocks not installed. Run: pip install pysocks")
        return False
    except Exception as e:
        logger.warning(f"Proxy test failed: {e}")
        return False


def get_chrome_proxy_options(proxy_host: str, proxy_port: int, proxy_type: str = "socks5") -> Dict:
    """
    Get Chrome options for proxy configuration.
    
    Args:
        proxy_host: Proxy server hostname or IP
        proxy_port: Proxy server port  
        proxy_type: Type of proxy
    
    Returns:
        Dict with Chrome proxy arguments
    """
    if proxy_type in ["socks5", "socks4"]:
        proxy_string = f"--proxy-server={proxy_type}://{proxy_host}:{proxy_port}"
    else:
        proxy_string = f"--proxy-server={proxy_host}:{proxy_port}"
    
    return {
        "proxy_arg": proxy_string,
        "proxy_type": proxy_type,
        "proxy_host": proxy_host,
        "proxy_port": proxy_port
    }


def setup_ssh_tunnel(ssh_host: str, ssh_port: int = 22, 
                     ssh_user: str = None, local_port: int = 1080) -> Tuple[bool, str]:
    """
    Instructions for setting up SSH SOCKS tunnel.
    
    This creates a SOCKS5 proxy through SSH that bypasses corporate network.
    
    Args:
        ssh_host: Remote SSH server (e.g., your home server or VPS)
        ssh_port: SSH port (default 22)
        ssh_user: SSH username
        local_port: Local SOCKS port (default 1080)
    
    Returns:
        Tuple of (success, message/instructions)
    """
    instructions = f"""
╔══════════════════════════════════════════════════════════════╗
║          SSH TUNNEL BYPASS INSTRUCTIONS                       ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  This creates a secure tunnel that bypasses corporate DLP.   ║
║                                                               ║
║  REQUIREMENTS:                                                ║
║  • A remote server with SSH access (home PC, VPS, etc.)      ║
║  • SSH client (built into Windows 10/11)                     ║
║                                                               ║
║  SETUP STEPS:                                                 ║
║                                                               ║
║  1. Open a NEW PowerShell window and run:                    ║
║                                                               ║
║     ssh -D {local_port} -N {ssh_user or 'user'}@{ssh_host}   ║
║                                                               ║
║  2. Keep that window open (it creates the tunnel)            ║
║                                                               ║
║  3. In config/settings.py, add:                              ║
║                                                               ║
║     use_proxy = True                                         ║
║     proxy_host = "127.0.0.1"                                 ║
║     proxy_port = {local_port}                                ║
║     proxy_type = "socks5"                                    ║
║                                                               ║
║  4. Run the bot - traffic will go through your tunnel!       ║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝
"""
    return True, instructions


def get_mobile_hotspot_instructions() -> str:
    """Get instructions for connecting to mobile hotspot."""
    return """
╔══════════════════════════════════════════════════════════════╗
║         MOBILE HOTSPOT BYPASS (RECOMMENDED)                   ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  This is the EASIEST and MOST RELIABLE bypass method!        ║
║                                                               ║
║  STEPS:                                                       ║
║                                                               ║
║  1. On your PHONE:                                           ║
║     • Go to Settings → Mobile Hotspot / Personal Hotspot     ║
║     • Turn ON the hotspot                                    ║
║     • Note the WiFi name and password                        ║
║                                                               ║
║  2. On your LAPTOP:                                          ║
║     • Click WiFi icon in taskbar                             ║
║     • Find your phone's hotspot name                         ║
║     • Connect to it                                          ║
║                                                               ║
║  3. Run the bot normally - it will bypass corporate DLP!     ║
║                                                               ║
║  WHY THIS WORKS:                                             ║
║  Your phone's internet goes through cellular network,        ║
║  completely bypassing Deloitte's Netskope/DLP software.     ║
║                                                               ║
║  DATA USAGE: ~50-100MB per job application session           ║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝
"""


def check_bypass_options() -> Dict:
    """
    Check available bypass options and return recommendations.
    
    Returns:
        Dict with available bypass methods and recommendations
    """
    results = {
        "mobile_hotspot": {"available": False, "network_name": None},
        "recommendations": [],
        "best_option": None
    }
    
    # Check for mobile hotspot
    hotspot_available, hotspot_name = detect_mobile_hotspot()
    results["mobile_hotspot"]["available"] = hotspot_available
    results["mobile_hotspot"]["network_name"] = hotspot_name
    
    if hotspot_available:
        results["recommendations"].append(
            f"📱 Mobile hotspot '{hotspot_name}' detected! Connect to it for best results."
        )
        results["best_option"] = "mobile_hotspot"
    else:
        results["recommendations"].append(
            "📱 Enable mobile hotspot on your phone and connect to it."
        )
        results["best_option"] = "mobile_hotspot"  # Still the best option
    
    results["recommendations"].append(
        "🔗 Alternative: Set up SSH tunnel if you have a home server or VPS."
    )
    
    return results


if __name__ == "__main__":
    print("\n" + "="*60)
    print("BYPASS OPTIONS CHECK")
    print("="*60)
    
    # Check for mobile hotspot
    print("\nChecking for mobile hotspot...")
    hotspot_available, hotspot_name = detect_mobile_hotspot()
    if hotspot_available:
        print(f"✅ Mobile hotspot detected: {hotspot_name}")
    else:
        print("❌ No mobile hotspot detected")
    
    # Print instructions
    print(get_mobile_hotspot_instructions())

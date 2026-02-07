"""
Network Security Check Module
Detects corporate DLP, SSL inspection, and security software that may block LinkedIn submissions.
"""

import subprocess
import socket
import ssl
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Known corporate security software processes
SECURITY_PROCESSES = [
    "netskopeagent", "nsagent", "stAgentSvc",  # Netskope
    "zscaler", "ZSATunnel", "ZSAService",       # Zscaler
    "forcepoint", "fppsvc",                      # Forcepoint
    "mcafee", "mfemms", "masvc",                 # McAfee
    "crowdstrike", "csfalconservice",            # CrowdStrike
    "sentinelone", "sentinelagent",              # SentinelOne
    "taniumclient",                              # Tanium
    "dlpuseragent", "epdlp", "mpdlpservice",    # DLP services
    "defendpointservice",                        # Avecto/BeyondTrust
    "symantec", "sepmaster"                      # Symantec
]

# Known SSL inspection certificate issuers
SSL_INSPECTION_ISSUERS = [
    "Netskope", "Zscaler", "Forcepoint", "BlueCoat",
    "Symantec", "McAfee", "Palo Alto", "Deloitte",
    "Corporate", "Enterprise", "Proxy"
]


def check_security_processes() -> Tuple[bool, List[str]]:
    """Check for running security/DLP processes."""
    found_processes = []
    
    try:
        # Get list of running processes
        result = subprocess.run(
            ["powershell", "-Command", 
             "Get-Process | Select-Object -ExpandProperty ProcessName"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            running_processes = result.stdout.lower().split('\n')
            
            for security_proc in SECURITY_PROCESSES:
                for running in running_processes:
                    if security_proc.lower() in running.strip():
                        found_processes.append(running.strip())
                        
    except Exception as e:
        logger.warning(f"Could not check security processes: {e}")
    
    return len(found_processes) > 0, list(set(found_processes))


def check_ssl_inspection() -> Tuple[bool, List[str]]:
    """Check for SSL inspection certificates in certificate store."""
    found_certs = []
    
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-ChildItem Cert:\\CurrentUser\\Root | Select-Object -ExpandProperty Issuer"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                for issuer in SSL_INSPECTION_ISSUERS:
                    if issuer.lower() in line.lower():
                        found_certs.append(line.strip()[:80])
                        break
                        
    except Exception as e:
        logger.warning(f"Could not check SSL certificates: {e}")
    
    return len(found_certs) > 0, list(set(found_certs))[:5]


def check_dlp_services() -> Tuple[bool, List[str]]:
    """Check for active DLP services."""
    found_services = []
    
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Service | Where-Object { $_.Status -eq 'Running' -and ($_.DisplayName -match 'DLP|Data Loss|Netskope|Zscaler') } | Select-Object -ExpandProperty DisplayName"],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.strip():
                    found_services.append(line.strip())
                    
    except Exception as e:
        logger.warning(f"Could not check DLP services: {e}")
    
    return len(found_services) > 0, found_services


def test_linkedin_connectivity() -> Tuple[bool, str]:
    """Test if LinkedIn API endpoints are accessible."""
    try:
        # Try to establish SSL connection to LinkedIn
        context = ssl.create_default_context()
        
        with socket.create_connection(("www.linkedin.com", 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname="www.linkedin.com") as ssock:
                cert = ssock.getpeercert()
                issuer = dict(x[0] for x in cert.get('issuer', []))
                issuer_org = issuer.get('organizationName', 'Unknown')
                
                # Check if certificate is from LinkedIn/DigiCert (legitimate) or corporate proxy
                legitimate_issuers = ['DigiCert', 'LinkedIn', 'Let\'s Encrypt', 'GlobalSign']
                
                for legit in legitimate_issuers:
                    if legit.lower() in issuer_org.lower():
                        return True, f"Direct connection (via {issuer_org})"
                
                # Likely intercepted
                return False, f"SSL intercepted by: {issuer_org}"
                
    except Exception as e:
        return False, f"Connection error: {str(e)[:50]}"


def run_full_security_check() -> Dict:
    """
    Run comprehensive security check and return results.
    
    Returns:
        Dict with check results and recommendations
    """
    results = {
        "is_corporate_network": False,
        "can_submit_applications": True,
        "issues": [],
        "warnings": [],
        "recommendations": [],
        "details": {}
    }
    
    # Check 1: Security processes
    has_security, processes = check_security_processes()
    results["details"]["security_processes"] = processes
    if has_security:
        results["issues"].append(f"Security software detected: {', '.join(processes[:3])}")
        results["is_corporate_network"] = True
    
    # Check 2: SSL inspection
    has_ssl_inspection, certs = check_ssl_inspection()
    results["details"]["ssl_inspection_certs"] = certs
    if has_ssl_inspection:
        results["issues"].append("SSL inspection certificates found")
        results["is_corporate_network"] = True
    
    # Check 3: DLP services
    has_dlp, services = check_dlp_services()
    results["details"]["dlp_services"] = services
    if has_dlp:
        results["issues"].append(f"DLP services active: {', '.join(services[:2])}")
        results["can_submit_applications"] = False  # DLP likely blocks submissions
    
    # Check 4: LinkedIn connectivity
    linkedin_ok, linkedin_msg = test_linkedin_connectivity()
    results["details"]["linkedin_connection"] = linkedin_msg
    if not linkedin_ok:
        results["issues"].append(f"LinkedIn connection: {linkedin_msg}")
        results["can_submit_applications"] = False
    
    # Generate recommendations
    if results["is_corporate_network"] or not results["can_submit_applications"]:
        results["recommendations"] = [
            "🔥 RECOMMENDED: Connect to mobile hotspot to bypass corporate network",
            "📱 Alternative: Use LinkedIn mobile app on your phone",
            "🏠 Alternative: Use a personal computer at home",
            "🔌 If on VPN: Try disconnecting from corporate VPN"
        ]
        
        if has_dlp:
            results["warnings"].append(
                "⚠️ DLP (Data Loss Prevention) is ACTIVE - LinkedIn submissions will likely fail with 500 errors"
            )
    
    return results


def print_security_report(results: Dict) -> None:
    """Print a formatted security report."""
    print("\n" + "="*60)
    print("🔒 NETWORK SECURITY CHECK REPORT")
    print("="*60)
    
    if results["can_submit_applications"] and not results["is_corporate_network"]:
        print("\n✅ Network looks good! You should be able to submit applications.")
    else:
        print("\n❌ ISSUES DETECTED:")
        for issue in results["issues"]:
            print(f"   • {issue}")
        
        if results["warnings"]:
            print("\n⚠️ WARNINGS:")
            for warning in results["warnings"]:
                print(f"   {warning}")
        
        print("\n💡 RECOMMENDATIONS:")
        for rec in results["recommendations"]:
            print(f"   {rec}")
    
    print("\n" + "="*60)


def check_and_warn() -> bool:
    """
    Quick check that returns True if network is safe, False if issues detected.
    Logs warnings if issues found.
    """
    results = run_full_security_check()
    
    if not results["can_submit_applications"]:
        logger.warning("="*50)
        logger.warning("⚠️ NETWORK SECURITY WARNING")
        logger.warning("="*50)
        for issue in results["issues"]:
            logger.warning(f"  • {issue}")
        logger.warning("")
        logger.warning("LinkedIn submissions may fail with 500 errors!")
        logger.warning("SOLUTION: Connect to mobile hotspot instead")
        logger.warning("="*50)
        return False
    
    return True


if __name__ == "__main__":
    # Run standalone check
    print("Running network security check...")
    results = run_full_security_check()
    print_security_report(results)

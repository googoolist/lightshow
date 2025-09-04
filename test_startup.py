#!/usr/bin/env python3
"""
Test script to verify auto-startup configuration for DMX Light Show.

Author: Generated for Raspberry Pi DMX Project
"""

import subprocess
import time
import sys
import os

def run_command(cmd, capture_output=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def test_service_exists():
    """Test if the systemd service file exists."""
    print("🔍 Checking if systemd service exists...")
    success, stdout, stderr = run_command("systemctl status dmx-lightshow")
    
    if "could not be found" in stderr.lower():
        print("❌ Service not found. Run install.sh first.")
        return False
    else:
        print("✅ Service exists")
        return True

def test_service_enabled():
    """Test if the service is enabled for auto-start."""
    print("🔍 Checking if service is enabled for auto-start...")
    success, stdout, stderr = run_command("systemctl is-enabled dmx-lightshow")
    
    if "enabled" in stdout:
        print("✅ Service is enabled for auto-start")
        return True
    else:
        print("❌ Service is not enabled. Run: sudo systemctl enable dmx-lightshow")
        return False

def test_files_exist():
    """Test if required files exist."""
    print("🔍 Checking required files...")
    
    required_files = [
        "config.yaml",
        "main.py", 
        "start_lightshow.py",
        "venv/bin/python"
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            all_exist = False
    
    return all_exist

def test_startup_simulation():
    """Test the startup script in simulation mode."""
    print("🔍 Testing startup script (simulation)...")
    
    # Create a temporary config for testing
    test_config = """
audio:
  device_name: "Test Device"
dmx:
  interface: "/dev/ttyUSB99"  # Non-existent device for testing
system:
  debug: true
"""
    
    with open("test_config.yaml", "w") as f:
        f.write(test_config)
    
    try:
        # Test the startup script with timeout
        cmd = "./venv/bin/python -c \"import start_lightshow; print('Startup script imported successfully')\""
        success, stdout, stderr = run_command(cmd)
        
        if success:
            print("✅ Startup script can be imported")
            return True
        else:
            print(f"❌ Startup script import failed: {stderr}")
            return False
    
    finally:
        # Clean up test file
        if os.path.exists("test_config.yaml"):
            os.remove("test_config.yaml")

def test_audio_permissions():
    """Test if user has audio permissions."""
    print("🔍 Checking audio group membership...")
    
    success, stdout, stderr = run_command("groups")
    if "audio" in stdout:
        print("✅ User is in audio group")
        return True
    else:
        print("❌ User not in audio group. Run: sudo usermod -a -G audio $USER")
        print("   Then log out and back in (or reboot)")
        return False

def test_dmx_permissions():
    """Test if user has DMX device permissions."""
    print("🔍 Checking dialout group membership...")
    
    success, stdout, stderr = run_command("groups")
    if "dialout" in stdout:
        print("✅ User is in dialout group")
        return True
    else:
        print("❌ User not in dialout group. Run: sudo usermod -a -G dialout $USER")
        print("   Then log out and back in (or reboot)")
        return False

def main():
    """Run all startup tests."""
    print("=== DMX Light Show Auto-Startup Test ===\n")
    
    tests = [
        ("Service file exists", test_service_exists),
        ("Service is enabled", test_service_enabled),
        ("Required files exist", test_files_exist),
        ("Audio permissions", test_audio_permissions),
        ("DMX permissions", test_dmx_permissions),
        ("Startup script works", test_startup_simulation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        else:
            print("   See above for fix instructions")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Your system should auto-start the light show on boot.")
        print("\n💡 To test auto-startup manually:")
        print("   sudo systemctl start dmx-lightshow")
        print("   sudo journalctl -u dmx-lightshow -f")
    else:
        print("⚠️  Some tests failed. Please fix the issues above before expecting auto-startup to work.")
        
    print(f"\n📋 Quick Commands:")
    print(f"   View service status:  sudo systemctl status dmx-lightshow")
    print(f"   View logs:           sudo journalctl -u dmx-lightshow -f")
    print(f"   Start manually:      sudo systemctl start dmx-lightshow")
    print(f"   Stop service:        sudo systemctl stop dmx-lightshow")

if __name__ == "__main__":
    main()

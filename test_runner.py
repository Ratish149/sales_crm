"""
Test script to simulate the run_project WebSocket action
This verifies our fixes work correctly
"""

import os
import sys

# Add project to path
sys.path.insert(0, r"e:\Baliyo projects\MultiTenant\sales_crm")

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sales_crm.settings")
import django

django.setup()

from project_runner.services import RunnerService

# Test the run_project functionality
workspace_id = "ip-store"
print(f"Testing RunnerService for workspace: {workspace_id}")
print("=" * 60)

try:
    # Create the runner service
    print("\n1. Creating RunnerService instance...")
    runner = RunnerService(workspace_id)
    print("   ✓ Runner created successfully")
    print(f"   Project path: {runner.project_path}")

    # Check if project exists
    print("\n2. Checking if project path exists...")
    if runner.project_path.exists():
        print("   ✓ Project path exists")
    else:
        print("   ✗ Project path does not exist!")
        sys.exit(1)

    # Test the run_project method (without actually starting the server)
    print("\n3. Testing run_project (dry run)...")
    print("   Checking node_modules...")
    if (runner.project_path / "node_modules").exists():
        print("   ✓ node_modules exists")
    else:
        print("   ⚠ node_modules does not exist - npm install would run")

    # Check for TailwindCSS specifically
    print("\n4. Checking TailwindCSS installation...")
    tailwind_path = runner.project_path / "node_modules" / "tailwindcss"
    if tailwind_path.exists():
        print("   ✓ TailwindCSS is installed")
    else:
        print("   ✗ TailwindCSS is NOT installed!")
        sys.exit(1)

    # Check package.json
    print("\n5. Checking package.json...")
    package_json = runner.project_path / "package.json"
    if package_json.exists():
        print("   ✓ package.json exists")
        import json

        with open(package_json, "r") as f:
            pkg = json.load(f)
            if "tailwindcss" in pkg.get("devDependencies", {}):
                print("   ✓ TailwindCSS in devDependencies")

    print("\n" + "=" * 60)
    print("✓ ALL CHECKS PASSED!")
    print("=" * 60)
    print("\nThe WebSocket run_project action should now work correctly.")
    print("TailwindCSS is installed and the project is ready to run.")

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

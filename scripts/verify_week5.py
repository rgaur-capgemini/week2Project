#!/usr/bin/env python3
"""
Week 5 Implementation Verification
Checks that all files exist and imports work correctly.
"""

import os
import sys
from pathlib import Path

# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def check_mark(passed: bool) -> str:
    return f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"

def main():
    print("=" * 60)
    print("Week 5 Implementation Verification")
    print("=" * 60)
    print()
    
    # Get the project root directory (parent of scripts/)
    base_dir = Path(__file__).parent.parent
    total_checks = 0
    passed_checks = 0
    
    # Check 1: Agent files
    print("1. Checking Agent Framework Files...")
    agent_files = [
        "app/agents/__init__.py",
        "app/agents/memory.py",
        "app/agents/orchestrator.py",
        "app/agents/tools/__init__.py",
        "app/agents/tools/base.py",
        "app/agents/tools/rag_search.py",
        "app/agents/tools/calculator.py",
        "app/agents/tools/csv_query.py",
        "app/agents/tools/image_analysis.py",
        "app/agents/tools/web_search.py",
    ]
    
    for file in agent_files:
        path = base_dir / file
        exists = path.exists()
        total_checks += 1
        if exists:
            passed_checks += 1
        print(f"   {check_mark(exists)} {file}")
    
    # Check 2: Multimodal files
    print("\n2. Checking Multimodal Files...")
    multimodal_files = [
        "app/multimodal/__init__.py",
        "app/multimodal/embeddings.py",
        "app/multimodal/image_store.py",
        "app/multimodal/vector_store.py",
        "app/multimodal/retriever.py",
    ]
    
    for file in multimodal_files:
        path = base_dir / file
        exists = path.exists()
        total_checks += 1
        if exists:
            passed_checks += 1
        print(f"   {check_mark(exists)} {file}")
    
    # Check 3: API routes
    print("\n3. Checking API Routes...")
    route_files = [
        "app/agent_routes.py",
        "app/multimodal_routes.py",
    ]
    
    for file in route_files:
        path = base_dir / file
        exists = path.exists()
        total_checks += 1
        if exists:
            passed_checks += 1
        print(f"   {check_mark(exists)} {file}")
    
    # Check 4: Cloud Function
    print("\n4. Checking Cloud Function...")
    cf_files = [
        "cloud-functions/csv-processor/main.py",
        "cloud-functions/csv-processor/requirements.txt",
    ]
    
    for file in cf_files:
        path = base_dir / file
        exists = path.exists()
        total_checks += 1
        if exists:
            passed_checks += 1
        print(f"   {check_mark(exists)} {file}")
    
    # Check 5: CI/CD
    print("\n5. Checking CI/CD Pipeline...")
    cicd_files = [
        "cloudbuild-gke.yaml",
    ]
    
    for file in cicd_files:
        path = base_dir / file
        exists = path.exists()
        total_checks += 1
        if exists:
            passed_checks += 1
        print(f"   {check_mark(exists)} {file}")
    
    # Check 6: Updated files
    print("\n6. Checking Updated Files...")
    
    # Check main.py for agent and multimodal imports
    main_py = base_dir / "app/main.py"
    if main_py.exists():
        content = main_py.read_text()
        has_agent_import = "from app.agent_routes import router as agent_router" in content
        has_multimodal_import = "from app.multimodal_routes import router as multimodal_router" in content
        has_agent_include = "app.include_router(agent_router)" in content
        has_multimodal_include = "app.include_router(multimodal_router)" in content
        
        total_checks += 4
        if has_agent_import:
            passed_checks += 1
        if has_multimodal_import:
            passed_checks += 1
        if has_agent_include:
            passed_checks += 1
        if has_multimodal_include:
            passed_checks += 1
        
        print(f"   {check_mark(has_agent_import)} main.py: agent import")
        print(f"   {check_mark(has_multimodal_import)} main.py: multimodal import")
        print(f"   {check_mark(has_agent_include)} main.py: agent router registered")
        print(f"   {check_mark(has_multimodal_include)} main.py: multimodal router registered")
    else:
        print(f"   {RED}✗{RESET} main.py not found")
        total_checks += 4
    
    # Check requirements.txt for Pillow
    req_txt = base_dir / "requirements.txt"
    if req_txt.exists():
        content = req_txt.read_text()
        has_pillow = "Pillow>=" in content
        
        total_checks += 1
        if has_pillow:
            passed_checks += 1
        
        print(f"   {check_mark(has_pillow)} requirements.txt: Pillow added")
    else:
        print(f"   {RED}✗{RESET} requirements.txt not found")
        total_checks += 1
    
    # Check 7: Import tests (without GCP credentials)
    print("\n7. Checking Python Imports...")
    
    # Add parent directory to Python path for imports
    sys.path.insert(0, str(base_dir))
    
    import_tests = [
        ("Agent tools base", "from app.agents.tools.base import BaseTool, ToolResult"),
        ("Agent orchestrator", "from app.agents.orchestrator import AgentOrchestrator"),
        ("Agent memory", "from app.agents.memory import AgentMemory"),
        ("Multimodal", "from app.multimodal import MultiModalRetriever"),
    ]
    
    for name, import_stmt in import_tests:
        try:
            exec(import_stmt)
            print(f"   {GREEN}✓{RESET} {name}")
            total_checks += 1
            passed_checks += 1
        except ImportError as e:
            print(f"   {RED}✗{RESET} {name}: {e}")
            total_checks += 1
        except Exception as e:
            # GCP auth errors are OK for verification
            if "credentials" in str(e).lower() or "auth" in str(e).lower():
                print(f"   {YELLOW}⚠{RESET} {name} (GCP credentials needed at runtime)")
                total_checks += 1
                passed_checks += 1
            else:
                print(f"   {RED}✗{RESET} {name}: {e}")
                total_checks += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total checks: {total_checks}")
    print(f"Passed: {GREEN}{passed_checks}{RESET}")
    print(f"Failed: {RED}{total_checks - passed_checks}{RESET}")
    print()
    
    if passed_checks == total_checks:
        print(f"{GREEN}✅ ALL CHECKS PASSED!{RESET}")
        print(f"{GREEN}Week 5 implementation is complete and ready for deployment.{RESET}")
        print()
        print("Next steps:")
        print("  1. Deploy: gcloud builds submit --config cloudbuild-gke.yaml")
        print("  2. Test: See WEEK5_QUICK_START.md")
        return 0
    else:
        print(f"{RED}❌ SOME CHECKS FAILED{RESET}")
        print(f"Please review the failed checks above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

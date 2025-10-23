"""
Test script to verify the development environment setup
"""

import sys
import os
from pathlib import Path

def test_python_environment():
    """Test Python version and basic imports"""
    print("🐍 Python Environment Test")
    print("=" * 40)
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    print(f"Current Working Directory: {os.getcwd()}")
    
    # Test core imports
    try:
        import pandas as pd
        import numpy as np
        import sklearn
        print("✅ Core data science libraries imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    return True

def test_project_structure():
    """Test that project structure is correctly set up"""
    print("\n📁 Project Structure Test")
    print("=" * 40)
    
    expected_dirs = [
        "stocksense",
        "smart-cart", 
        "compliance-scout",
        "shared",
        "docs"
    ]
    
    missing_dirs = []
    for dir_name in expected_dirs:
        if Path(dir_name).exists():
            print(f"✅ {dir_name}/ directory exists")
        else:
            print(f"❌ {dir_name}/ directory missing")
            missing_dirs.append(dir_name)
    
    return len(missing_dirs) == 0

def test_stocksense_setup():
    """Test StockSense project setup"""
    print("\n📊 StockSense Setup Test")
    print("=" * 40)
    
    stocksense_files = [
        "stocksense/README.md",
        "stocksense/requirements.txt", 
        "stocksense/src/model.py",
        "stocksense/data/data_generation.py"
    ]
    
    for file_path in stocksense_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")

def main():
    """Run all tests"""
    print("🧪 Walmart AI Portfolio Environment Test")
    print("=" * 50)
    
    # Run tests
    python_ok = test_python_environment()
    structure_ok = test_project_structure()
    test_stocksense_setup()
    
    print("\n🎯 Test Summary")
    print("=" * 40)
    if python_ok and structure_ok:
        print("✅ Environment setup is complete and working!")
        print("🚀 Ready to start development!")
        
        print("\n📋 Next Steps:")
        print("1. Navigate to stocksense/data/ and run: python data_generation.py")
        print("2. Open stocksense/notebooks/stocksense_analysis.ipynb")
        print("3. Start building your AI portfolio!")
    else:
        print("❌ Some issues found. Please check the errors above.")

if __name__ == "__main__":
    main()
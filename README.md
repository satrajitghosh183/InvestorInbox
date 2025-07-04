# 🚀 Email Enrichment App - Setup & Build Guide

A Windows application for extracting and enriching email contacts with AI-powered insights.

## 📥 Download & Install

### **Get the Code**
```bash
# Option 1: GitHub
git clone https://github.com/your-username/email-enrichment-demo.git
cd email-enrichment-demo

# Option 2: Download ZIP and extract to your folder
# Option 3: Download from Google Drive [Your Link]
```

### **Setup Environment**
```bash
# Create virtual environment
python -m venv email_enrichment_env
email_enrichment_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🔨 Build Windows Executable

```bash
# Simple build
python build_exe.py

# Build options
python build_exe.py --mode console    # Shows terminal
python build_exe.py --mode gui        # No terminal window
python build_exe.py --no-test         # Skip testing

# Alternative: Direct PyInstaller
pyinstaller --clean --noconfirm app.spec
```

**Output:** `dist/EmailEnrichmentApp.exe` (~200-400MB)

---

## 🚀 How to Run

### **Option 1: Through app.py (New GUI Wrapper)**

```bash
# Setup wizard (first time)
python app.py --setup

# Launch GUI
python app.py --gui

# Quick extract
python app.py --quick-extract

# Command line with app.py
python app.py --extract --providers gmail --export-format excel
python app.py --status
```

### **Option 2: Direct main.py (Your Original)**

```bash
cd src

# Your existing commands work as before
python main.py --status
python main.py --extract --providers gmail outlook
python main.py --extract --enhanced-scoring --enrich --export-format excel
python main.py --test-ai --test-apis
python main.py --list-accounts

cd ..
```

### **Option 3: Built Executable**

```bash
cd dist

# First time setup
EmailEnrichmentApp.exe --setup

# Launch GUI
EmailEnrichmentApp.exe --gui

# Command line usage
EmailEnrichmentApp.exe --extract --providers gmail --export-format excel
EmailEnrichmentApp.exe --status

# Quick shortcuts (double-click these)
Run_Setup.bat
Run_GUI.bat
Quick_Extract.bat
```

---

## 📋 Key Commands

### **Setup & Status**
```bash
--setup          # Interactive setup wizard
--status         # Show configuration
--test-accounts  # Test email connections
```

### **Extraction**
```bash
--extract                    # Basic extraction
--providers gmail outlook    # Specify providers
--days-back 60              # Look back N days
--enhanced-scoring          # AI scoring
--enrich                    # API enrichment
--export-format excel       # Export format
```

### **Interface**
```bash
--gui            # Launch GUI
--quick-extract  # Fast extraction with defaults
```

---

## 🎯 Quick Start

1. **Download** → Extract project
2. **Install** → `pip install -r requirements.txt`
3. **Setup** → `python app.py --setup` (configure accounts/APIs)
4. **Extract** → `python app.py --quick-extract`
5. **Build** → `python build_exe.py` (optional)

**That's it!** Use `app.py --gui` for GUI interface or `src/main.py` for your original commands.
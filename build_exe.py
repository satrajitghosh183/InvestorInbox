"""
Build script for Email Enrichment App
Creates Windows executable using PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse

class AppBuilder:
    """Builder for Email Enrichment App executable"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.spec_file = self.project_root / "app.spec"
        
    def clean_build(self):
        """Clean previous build artifacts"""
        print("🧹 Cleaning previous build artifacts...")
        
        dirs_to_clean = [self.dist_dir, self.build_dir]
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"   Removed: {dir_path}")
        
        # Clean __pycache__ directories
        for pycache in self.project_root.rglob("__pycache__"):
            shutil.rmtree(pycache)
            print(f"   Removed: {pycache}")
        
        print("✅ Clean completed")
    
    def check_dependencies(self):
        """Check if all dependencies are installed"""
        print("🔍 Checking dependencies...")
        
        required_packages = [
            'pyinstaller',
            'pyyaml',
            'keyring',
            'cryptography',
            'google-auth',
            'google-auth-oauthlib',
            'google-api-python-client',
            'pandas',
            'openpyxl'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"   ✅ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"   ❌ {package}")
        
        if missing_packages:
            print("\n❌ Missing dependencies:")
            print("Install with:")
            print(f"pip install {' '.join(missing_packages)}")
            return False
        
        print("✅ All dependencies available")
        return True
    
    def create_version_info(self):
        """Create version info file for Windows executable"""
        version_info = """
# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1,0,0,0),
    prodvers=(1,0,0,0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Email Enrichment Solutions'),
        StringStruct(u'FileDescription', u'Email Contact Enrichment Application'),
        StringStruct(u'FileVersion', u'1.0.0.0'),
        StringStruct(u'InternalName', u'EmailEnrichmentApp'),
        StringStruct(u'LegalCopyright', u'Copyright (C) 2025'),
        StringStruct(u'OriginalFilename', u'EmailEnrichmentApp.exe'),
        StringStruct(u'ProductName', u'Email Enrichment App'),
        StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
        
        version_file = self.project_root / "version_info.txt"
        with open(version_file, 'w') as f:
            f.write(version_info.strip())
        
        print("✅ Version info created")
        return version_file
    
    def build_executable(self, mode='console'):
        """Build the executable using PyInstaller"""
        print(f"🔨 Building executable ({mode} mode)...")
        
        # Determine which executable to build
        if mode == 'gui':
            target_name = 'EmailEnrichmentApp_GUI'
        else:
            target_name = 'EmailEnrichmentApp'
        
        # Build command
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--clean',
            '--noconfirm',
            str(self.spec_file)
        ]
        
        try:
            # Run PyInstaller
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✅ Build completed successfully")
            
            # Check if executable was created
            exe_path = self.dist_dir / f"{target_name}.exe"
            if exe_path.exists():
                print(f"📦 Executable created: {exe_path}")
                print(f"📊 Size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
                return exe_path
            else:
                print("❌ Executable not found after build")
                return None
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Build failed: {e}")
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
            return None
    
    def create_installer_package(self, exe_path):
        """Create a simple installer package"""
        print("📦 Creating installer package...")
        
        # Create package directory
        package_dir = self.dist_dir / "EmailEnrichmentApp_Package"
        package_dir.mkdir(exist_ok=True)
        
        # Copy executable
        package_exe = package_dir / "EmailEnrichmentApp.exe"
        shutil.copy2(exe_path, package_exe)
        
        # Create README
        readme_content = """
# Email Enrichment App

## Installation
1. Copy EmailEnrichmentApp.exe to any folder on your computer
2. Run EmailEnrichmentApp.exe
3. If this is your first time, run: EmailEnrichmentApp.exe --setup

## Usage
- GUI Mode: Double-click the executable or run with --gui
- CLI Mode: Run from command prompt with various options
- Setup: Use --setup to configure email accounts and API keys

## Getting Started
1. Run the setup wizard to configure your email accounts
2. Add API keys for enrichment services (optional)
3. Start extracting and enriching your contacts!

## Support
For issues or questions, check the documentation or configuration files.
"""
        
        readme_file = package_dir / "README.txt"
        with open(readme_file, 'w') as f:
            f.write(readme_content.strip())
        
        # Create batch files for common operations
        setup_bat = package_dir / "Run_Setup.bat"
        with open(setup_bat, 'w') as f:
            f.write('@echo off\n')
            f.write('EmailEnrichmentApp.exe --setup\n')
            f.write('pause\n')
        
        gui_bat = package_dir / "Run_GUI.bat"
        with open(gui_bat, 'w') as f:
            f.write('@echo off\n')
            f.write('EmailEnrichmentApp.exe --gui\n')
        
        quick_extract_bat = package_dir / "Quick_Extract.bat"
        with open(quick_extract_bat, 'w') as f:
            f.write('@echo off\n')
            f.write('EmailEnrichmentApp.exe --quick-extract\n')
            f.write('pause\n')
        
        print(f"✅ Package created: {package_dir}")
        return package_dir
    
    def test_executable(self, exe_path):
        """Test the built executable"""
        print("🧪 Testing executable...")
        
        try:
            # Test help command
            result = subprocess.run([str(exe_path), '--help'], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Executable runs successfully")
                return True
            else:
                print(f"❌ Executable test failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⚠️ Executable test timed out")
            return False
        except Exception as e:
            print(f"❌ Executable test error: {e}")
            return False
    
    def build(self, clean=True, test=True, package=True, mode='console'):
        """Complete build process"""
        print("🚀 BUILDING EMAIL ENRICHMENT APP")
        print("=" * 50)
        
        # Clean previous builds
        if clean:
            self.clean_build()
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        # Create version info
        self.create_version_info()
        
        # Build executable
        exe_path = self.build_executable(mode)
        if not exe_path:
            return False
        
        # Test executable
        if test:
            if not self.test_executable(exe_path):
                print("⚠️ Warning: Executable test failed")
        
        # Create package
        if package:
            package_dir = self.create_installer_package(exe_path)
            print(f"\n🎉 BUILD COMPLETE!")
            print(f"📦 Package: {package_dir}")
            print(f"🚀 Executable: {exe_path}")
        
        return True


def main():
    """Main build script entry point"""
    parser = argparse.ArgumentParser(description="Build Email Enrichment App executable")
    parser.add_argument('--no-clean', action='store_true', help="Don't clean previous builds")
    parser.add_argument('--no-test', action='store_true', help="Don't test executable")
    parser.add_argument('--no-package', action='store_true', help="Don't create package")
    parser.add_argument('--mode', choices=['console', 'gui'], default='console',
                       help="Build mode (console or gui)")
    
    args = parser.parse_args()
    
    builder = AppBuilder()
    
    try:
        success = builder.build(
            clean=not args.no_clean,
            test=not args.no_test,
            package=not args.no_package,
            mode=args.mode
        )
        
        if success:
            print("\n✅ Build completed successfully!")
            print("\nTo test your executable:")
            print("1. Navigate to the dist folder")
            print("2. Run EmailEnrichmentApp.exe --setup")
            print("3. Configure your accounts and API keys")
            print("4. Run EmailEnrichmentApp.exe --gui or --quick-extract")
        else:
            print("\n❌ Build failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ Build cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Build error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
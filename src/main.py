# #!/usr/bin/env python3
# """
# Simple main application for testing
# """

# import sys
# import os
# import asyncio
# import argparse
# from pathlib import Path

# # Add src directory to path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# from utils.logging_config import setup_logging
# from providers.provider_factory import get_provider_factory
# from core.models import Contact

# setup_logging()

# async def main():
#     """Simple main function"""
    
#     parser = argparse.ArgumentParser(description="Email Enrichment System")
#     parser.add_argument("--config-summary", action="store_true", help="Show config summary")
#     parser.add_argument("--setup-providers", action="store_true", help="Setup providers")
#     parser.add_argument("--list-providers", action="store_true", help="List providers")
#     parser.add_argument("--test", action="store_true", help="Run test")
#     parser.add_argument("--providers", nargs="+", help="Specify providers")
    
#     args = parser.parse_args()
    
#     if args.config_summary:
#         print("📊 Configuration Summary:")
#         print("  Environment: Development")
#         print("  Providers: Gmail (if configured)")
#         print("  Status: Basic setup")
#         return
    
#     if args.list_providers:
#         factory = get_provider_factory()
#         configs = factory.load_provider_configs()
#         print(f"Available providers: {list(configs.keys())}")
#         return
    
#     if args.setup_providers:
#         print("🔍 Checking provider setup...")
#         factory = get_provider_factory()
#         configs = factory.load_provider_configs()
        
#         for provider_id in configs:
#             try:
#                 provider = await factory.create_provider(provider_id)
#                 if await provider.authenticate():
#                     print(f"✅ {provider_id}: Authentication successful")
#                 else:
#                     print(f"❌ {provider_id}: Authentication failed")
#             except Exception as e:
#                 print(f"❌ {provider_id}: Error - {e}")
#         return
    
#     if args.test:
#         print("🧪 Running test...")
#         factory = get_provider_factory()
#         configs = factory.load_provider_configs()
        
#         if not configs:
#             print("❌ No providers configured")
#             print("💡 Add gmail_credentials.json to config/ directory")
#             return
        
#         for provider_id in configs:
#             try:
#                 provider = await factory.create_provider(provider_id)
#                 if await provider.authenticate():
#                     contacts = await provider.extract_contacts(days_back=7, max_emails=10)
#                     print(f"✅ {provider_id}: Found {len(contacts)} contacts")
                    
#                     # Show sample contacts
#                     for i, contact in enumerate(contacts[:3]):
#                         print(f"  {i+1}. {contact.name} ({contact.email})")
#                 else:
#                     print(f"❌ {provider_id}: Authentication failed")
#             except Exception as e:
#                 print(f"❌ {provider_id}: Error - {e}")
#         return
    
#     print("📧 Email Enrichment System")
#     print("Use --help for available commands")

# if __name__ == "__main__":
#     asyncio.run(main())


#!/usr/bin/env python3
"""
Enhanced main application with export functionality
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.logging_config import setup_logging
from providers.provider_factory import get_provider_factory
from core.models import Contact
# Import enrichment and export modules
try:
    from enrichment.enrichment import ContactEnricher
    ENRICHMENT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Enrichment module not available: {e}")
    ENRICHMENT_AVAILABLE = False

try:
    from exporters.excel_exporter import EnhancedExcelExporter
    EXCEL_EXPORT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Excel exporter not available: {e}")
    EXCEL_EXPORT_AVAILABLE = False

setup_logging()

async def main():
    """Enhanced main function with export support"""
    
    parser = argparse.ArgumentParser(description="Email Enrichment System")
    parser.add_argument("--config-summary", action="store_true", help="Show config summary")
    parser.add_argument("--setup-providers", action="store_true", help="Setup providers")
    parser.add_argument("--list-providers", action="store_true", help="List providers")
    parser.add_argument("--test", action="store_true", help="Run test")
    parser.add_argument("--providers", nargs="+", help="Specify providers", default=None)
    parser.add_argument("--export-format", choices=["excel", "csv", "json"], help="Export format")
    parser.add_argument("--days-back", type=int, default=30, help="Days to look back for emails")
    parser.add_argument("--max-emails", type=int, default=1000, help="Maximum emails to process")
    parser.add_argument("--output-file", help="Output file name")
    parser.add_argument("--enrich", action="store_true", help="Enrich contacts with additional data")
    parser.add_argument("--analytics", action="store_true", help="Include analytics in export")
    
    args = parser.parse_args()
    
    if args.config_summary:
        print("📊 Configuration Summary:")
        print("  Environment: Development")
        print("  Providers: Gmail (if configured)")
        print("  Enrichment: Available")
        print("  Export formats: Excel, CSV, JSON")
        print("  Status: Ready")
        return
    
    if args.list_providers:
        factory = get_provider_factory()
        configs = factory.load_provider_configs()
        print(f"📋 Available providers: {list(configs.keys())}")
        if not configs:
            print("💡 Add provider credentials to enable:")
            print("  - Gmail: config/gmail_credentials.json")
            print("  - Outlook: Set OUTLOOK_CLIENT_ID and OUTLOOK_CLIENT_SECRET env vars")
            print("  - Yahoo: Set YAHOO_EMAIL and YAHOO_APP_PASSWORD env vars")
        return
    
    if args.setup_providers:
        print("🔍 Checking provider setup...")
        factory = get_provider_factory()
        configs = factory.load_provider_configs()
        
        if not configs:
            print("❌ No providers configured")
            print("💡 Setup instructions:")
            print("  1. Download Gmail credentials from Google Cloud Console")
            print("  2. Save as config/gmail_credentials.json")
            print("  3. Run setup again")
            return
        
        for provider_id in configs:
            try:
                print(f"🔄 Testing {provider_id}...")
                provider = await factory.create_provider(provider_id)
                
                if await provider.authenticate():
                    account_info = await provider.get_account_info()
                    print(f"✅ {provider_id}: Connected to {account_info.get('email', 'Unknown')}")
                    
                    # Test connection
                    if await provider.test_connection():
                        print(f"   📡 Connection test: Passed")
                    else:
                        print(f"   📡 Connection test: Failed")
                else:
                    print(f"❌ {provider_id}: Authentication failed")
                    
            except Exception as e:
                print(f"❌ {provider_id}: Error - {str(e)[:100]}...")
        
        await factory.cleanup_all_providers()
        return
    
    if args.test or args.export_format:
        print("🧪 Running email extraction and enrichment...")
        factory = get_provider_factory()
        configs = factory.load_provider_configs()
        
        if not configs:
            print("❌ No providers configured")
            print("💡 Run --setup-providers first")
            return
        
        # Filter providers if specified
        if args.providers:
            configs = {k: v for k, v in configs.items() if k in args.providers}
            if not configs:
                print(f"❌ No valid providers found from: {args.providers}")
                return
        
        all_contacts = []
        provider_results = {}
        
        # Extract contacts from all providers
        for provider_id in configs:
            try:
                print(f"📧 Extracting from {provider_id}...")
                provider = await factory.create_provider(provider_id)
                
                if await provider.authenticate():
                    contacts = await provider.extract_contacts(
                        days_back=args.days_back,
                        max_emails=args.max_emails
                    )
                    
                    provider_results[provider_id] = contacts
                    all_contacts.extend(contacts)
                    
                    print(f"   Found {len(contacts)} contacts")
                    
                    # Show sample contacts
                    for i, contact in enumerate(contacts[:3]):
                        strength = contact.calculate_relationship_strength()
                        print(f"   {i+1}. {contact.name} ({contact.email}) - {strength:.1%} strength")
                    
                    if len(contacts) > 3:
                        print(f"   ... and {len(contacts) - 3} more")
                        
                else:
                    print(f"❌ {provider_id}: Authentication failed")
                    
            except Exception as e:
                print(f"❌ {provider_id}: Error - {str(e)[:100]}...")
                continue
        
        # Merge and deduplicate contacts
        if all_contacts:
            merged_contacts = factory.merge_contacts_from_providers(provider_results)
            print(f"\n📊 Summary: {len(merged_contacts)} unique contacts after deduplication")
            
            # Enrich contacts if requested
            if args.enrich and ENRICHMENT_AVAILABLE:
                print("🔍 Enriching contacts with additional data...")
                enricher = ContactEnricher()
                try:
                    enriched_contacts = await enricher.enrich_contacts(merged_contacts)
                    print(f"✅ Enrichment completed for {len(enriched_contacts)} contacts")
                    merged_contacts = enriched_contacts
                except Exception as e:
                    print(f"⚠️ Enrichment failed: {e}")
                    print("📝 Continuing with basic contact data...")
                finally:
                    await enricher.cleanup()
            elif args.enrich and not ENRICHMENT_AVAILABLE:
                print("⚠️ Enrichment requested but module not available")
            
            # Export if format specified
            if args.export_format:
                print(f"📤 Exporting to {args.export_format.upper()}...")
                
                try:
                    if args.export_format == "excel" and EXCEL_EXPORT_AVAILABLE:
                        exporter = EnhancedExcelExporter()
                        filename = args.output_file
                        
                        if args.analytics:
                            # Create comprehensive analytics dashboard
                            export_path = await exporter.export_analytics_dashboard(merged_contacts)
                            print(f"✅ Analytics dashboard exported: {export_path}")
                        else:
                            # Standard export with analytics
                            export_path = await exporter.export_contacts(
                                contacts=merged_contacts,
                                filename=filename,
                                include_analytics=True,
                                include_charts=True
                            )
                            print(f"✅ Excel export completed: {export_path}")
                    
                    elif args.export_format == "excel" and not EXCEL_EXPORT_AVAILABLE:
                        print("❌ Excel export requested but module not available")
                        print("💡 Check that the enrichment and exporters modules are properly set up")
                        print("💡 Files should be at: src/enrichment/enrichment.py and src/exporters/excel_exporter.py")
                        return
                    
                    elif args.export_format == "csv":
                        # Basic CSV export
                        import pandas as pd
                        
                        # Convert contacts to DataFrame
                        data = []
                        for contact in merged_contacts:
                            data.append({
                                'Name': contact.name,
                                'Email': contact.email,
                                'Provider': contact.provider.value,
                                'Frequency': contact.frequency,
                                'Location': contact.location,
                                'Net Worth': contact.estimated_net_worth,
                                'Job Title': contact.job_title,
                                'Company': contact.company,
                                'Relationship Strength': f"{contact.calculate_relationship_strength():.1%}",
                                'Data Source': contact.data_source,
                                'Confidence': contact.confidence
                            })
                        
                        df = pd.DataFrame(data)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        csv_filename = args.output_file or f"contacts_{timestamp}.csv"
                        
                        # Ensure exports directory exists
                        exports_dir = Path("exports")
                        exports_dir.mkdir(exist_ok=True)
                        csv_path = exports_dir / csv_filename
                        
                        df.to_csv(csv_path, index=False)
                        print(f"✅ CSV export completed: {csv_path}")
                    
                    elif args.export_format == "json":
                        import json
                        
                        # Convert contacts to JSON
                        data = []
                        for contact in merged_contacts:
                            data.append({
                                'name': contact.name,
                                'email': contact.email,
                                'provider': contact.provider.value,
                                'frequency': contact.frequency,
                                'sent_to': contact.sent_to,
                                'received_from': contact.received_from,
                                'location': contact.location,
                                'estimated_net_worth': contact.estimated_net_worth,
                                'job_title': contact.job_title,
                                'company': contact.company,
                                'relationship_strength': contact.calculate_relationship_strength(),
                                'data_source': contact.data_source,
                                'confidence': contact.confidence,
                                'domain': contact.domain,
                                'first_seen': contact.first_seen.isoformat(),
                                'last_seen': contact.last_seen.isoformat()
                            })
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        json_filename = args.output_file or f"contacts_{timestamp}.json"
                        
                        # Ensure exports directory exists
                        exports_dir = Path("exports")
                        exports_dir.mkdir(exist_ok=True)
                        json_path = exports_dir / json_filename
                        
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        
                        print(f"✅ JSON export completed: {json_path}")
                
                except Exception as e:
                    print(f"❌ Export failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Show top contacts
            if not args.export_format:  # Only show if not exporting
                print(f"\n🏆 Top 5 contacts by relationship strength:")
                for i, contact in enumerate(merged_contacts[:5], 1):
                    strength = contact.calculate_relationship_strength()
                    location = contact.location or "Unknown location"
                    net_worth = contact.estimated_net_worth or "Unknown"
                    print(f"   {i}. {contact.name} ({contact.email})")
                    print(f"      📍 {location} | 💰 {net_worth} | 🤝 {strength:.1%} strength")
        
        else:
            print("❌ No contacts found")
        
        # Cleanup
        await factory.cleanup_all_providers()
        return
    
    # Default help message
    print("📧 Email Enrichment System")
    print("\nAvailable commands:")
    print("  --list-providers      List configured providers")
    print("  --setup-providers     Test provider authentication")
    print("  --test               Extract sample contacts")
    print("  --export-format      Export contacts (excel/csv/json)")
    print("  --enrich             Enrich contacts with additional data")
    print("  --analytics          Create analytics dashboard")
    print("\nExamples:")
    print("  python src/main.py --test --providers gmail")
    print("  python src/main.py --test --export-format excel --enrich")
    print("  python src/main.py --test --export-format excel --analytics")
    print("  python src/main.py --setup-providers")

if __name__ == "__main__":
    asyncio.run(main())
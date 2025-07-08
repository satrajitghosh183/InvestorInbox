import sys
import os
import asyncio
import argparse
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json
import os
import sys

# Force UTF-8 encoding for console output on Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # For Python 3.7+
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


# Add src directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.logging_config import setup_logging
from providers.provider_factory import get_provider_factory
from core.models import Contact

# Import enhanced contact scorer
try:
    # from contact_scorer import EnhancedContactScoringEngine
    from intelligence.contact_scorer import EnhancedContactScoringEngine
    ENHANCED_SCORING_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Enhanced scoring not available: {e}")
    ENHANCED_SCORING_AVAILABLE = False

# FIXED: Import from enrichment module
try:
    from enrichment import ContactEnricher, ENRICHMENT_AVAILABLE
    if not ENRICHMENT_AVAILABLE:
        print("⚠️ Note: Full enrichment functionality not available")
except ImportError as e:
    print(f"⚠️ Enrichment module not available: {e}")
    class ContactEnricher:
        def __init__(self):
            pass
        async def enrich_contacts(self, contacts):
            return contacts
        async def cleanup(self):
            pass
    ENRICHMENT_AVAILABLE = False

# Import Excel exporter with comprehensive fallback
try:
    from exporters.excel_exporter import EnhancedExcelExporter
    EXCEL_EXPORT_AVAILABLE = True
    print("[OK] Excel exporter loaded from exporters directory")
except ImportError:
    try:
        from excel_exporter import EnhancedExcelExporter
        EXCEL_EXPORT_AVAILABLE = True
        print("[OK] Excel exporter loaded from current directory")
    except ImportError:
        EXCEL_EXPORT_AVAILABLE = False
        print("⚠️ Excel exporter not available")

setup_logging()

def check_all_provider_status():
    """Check status of all providers and services"""
    
    print("\n📋 COMPREHENSIVE SYSTEM STATUS:")
    print("=" * 60)
    
    # Email Providers
    print("\n[EMAIL] EMAIL PROVIDERS:")
    print("-" * 20)
    
    config_dir = Path("config")
    
    # Gmail Status
    gmail_creds = config_dir / "gmail_credentials.json"
    gmail_specific_creds = list(config_dir.glob("gmail_*_credentials.json"))
    gmail_configured = gmail_creds.exists() or bool(gmail_specific_creds)
    print(f"  Gmail: {'[OK] CONFIGURED' if gmail_configured else '[FAIL] NOT CONFIGURED'}")
    
    if gmail_configured:
        if gmail_creds.exists():
            print(f"    📄 Primary: {gmail_creds}")
        for cred_file in gmail_specific_creds:
            import re
            pattern = r'gmail_([^_]+@[^_]+)_credentials\.json'
            match = re.match(pattern, cred_file.name)
            email = match.group(1) if match else "unknown"
            print(f"    📄 Account: {email}")
    
    # Other providers
    providers = [
        ("Outlook", os.getenv('OUTLOOK_CLIENT_ID') and os.getenv('OUTLOOK_CLIENT_SECRET')),
        ("Yahoo", os.getenv('YAHOO_EMAIL') and os.getenv('YAHOO_APP_PASSWORD')),
        ("iCloud", os.getenv('ICLOUD_EMAIL') and os.getenv('ICLOUD_APP_PASSWORD'))
    ]
    
    for provider, configured in providers:
        print(f"  {provider}: {'[OK] CONFIGURED' if configured else '[FAIL] NOT CONFIGURED'}")
    
    # Enrichment Services
    print("\n🔍 ENRICHMENT SERVICES:")
    print("-" * 25)
    
    enrichment_services = [
        ("Clearbit", os.getenv('CLEARBIT_API_KEY')),
        ("Hunter.io", os.getenv('HUNTER_API_KEY')),
        ("People Data Labs", os.getenv('PDL_API_KEY')),
      ]
    for service, configured in enrichment_services:
        print(f"  {service}: {'[OK] CONFIGURED' if configured else '[FAIL] NOT CONFIGURED'}")
    
    # AI Services
    print("\n🤖 AI SERVICES:")
    print("-" * 15)
    
    ai_services = [
        ("OpenAI", os.getenv('OPENAI_API_KEY')),
        ("HuggingFace", check_huggingface_availability()),
        ("Enhanced Scoring", ENHANCED_SCORING_AVAILABLE)
    ]
    
    for service, available in ai_services:
        print(f"  {service}: {'[OK] AVAILABLE' if available else '[FAIL] LIMITED'}")
    
    # System Components
    print("\n[STATS] SYSTEM COMPONENTS:")
    print("-" * 20)
    
    components = [
        ("Contact Enrichment", ENRICHMENT_AVAILABLE),
        ("Excel Export", EXCEL_EXPORT_AVAILABLE),
        ("Enhanced Scoring", ENHANCED_SCORING_AVAILABLE),
        ("Multi-Account Support", True)
    ]
    
    for component, available in components:
        print(f"  {component}: {'[OK] AVAILABLE' if available else '[FAIL] LIMITED'}")
    
    # Count configured services
    # email_configured = sum([gmail_configured, *[configured for _, configured in providers]])
    email_configured = sum([bool(gmail_configured)] + [bool(configured) for _, configured in providers])
    enrichment_configured = sum([bool(configured) for _, configured in enrichment_services])
    ai_configured = sum([bool(available) for _, available in ai_services])
    
    print(f"\n📈 CONFIGURATION SUMMARY:")
    print(f"  Email Providers: {email_configured}/4 configured")
    print(f"  Enrichment APIs: {enrichment_configured}/5 configured")
    print(f"  AI Services: {ai_configured}/3 available")
    print(f"  Overall Readiness: {((email_configured + enrichment_configured + ai_configured) / 12) * 100:.0f}%")
    
    if email_configured == 0:
        print("\n⚠️  WARNING: No email providers configured!")
        print("   At least one email provider is required.")
def safe_datetime_diff(dt1, dt2=None):
    """Safely calculate datetime difference handling timezone-aware/naive datetimes"""
    if dt2 is None:
        dt2 = datetime.now()
    
    # If one is timezone-aware and other is naive, make both timezone-aware
    if dt1.tzinfo is not None and dt2.tzinfo is None:
        dt2 = dt2.replace(tzinfo=timezone.utc)
    elif dt1.tzinfo is None and dt2.tzinfo is not None:
        dt1 = dt1.replace(tzinfo=timezone.utc)
    elif dt1.tzinfo is None and dt2.tzinfo is None:
        # Both naive, use as-is
        pass
    
    return (dt2 - dt1).days
def check_huggingface_availability():
    """Check if HuggingFace NLP is available"""
    try:
        import transformers
        import torch
        return True
    except ImportError:
        return False

async def extract_and_score_contacts(factory, provider_filter=None, days_back=30, max_emails=1000, use_enhanced_scoring=True):
    """Extract contacts and apply enhanced scoring"""
    
    print("[START] ENHANCED CONTACT EXTRACTION & SCORING:")
    print("=" * 55)
    
    # Initialize enhanced scorer
    scorer = None
    if use_enhanced_scoring and ENHANCED_SCORING_AVAILABLE:
        try:
            scorer = EnhancedContactScoringEngine()
            print("[OK] Enhanced scoring engine initialized")
        except Exception as e:
            print(f"⚠️ Enhanced scoring failed to initialize: {e}")
            print("📝 Falling back to basic scoring")
            scorer = None
    
    # Get all available providers
    try:
        providers = await factory.get_all_available_providers()
    except Exception as e:
        print(f"[FAIL] Failed to get providers: {e}")
        return [], {}, None
    
    if not providers:
        print("[FAIL] No providers available")
        return [], {}, scorer
    
    # Filter providers if specified
    if provider_filter:
        filtered_providers = {}
        for provider_name in provider_filter:
            if provider_name in providers:
                filtered_providers[provider_name] = providers[provider_name]
        providers = filtered_providers
    
    if not providers:
        print("[FAIL] No matching providers found")
        return [], {}, scorer
    
    # Extract contacts from all providers
    print(f"[EMAIL] Processing {sum(len(instances) for instances in providers.values())} accounts...")
    
    all_contacts = await factory.extract_contacts_from_providers(
        providers,
        days_back=days_back,
        max_emails=max_emails
    )
    
    # Show extraction summary
    print(f"\n[STATS] EXTRACTION SUMMARY:")
    total_contacts = 0
    
    for provider_name, contacts in all_contacts.items():
        contact_count = len(contacts)
        total_contacts += contact_count
        print(f"   {provider_name}: {contact_count} contacts")
    
    # Merge contacts across all accounts
    merged_contacts = factory.merge_contacts_from_providers(all_contacts)
    
    print(f"\n[STATS] MERGE SUMMARY:")
    print(f"   Total contacts before merge: {total_contacts}")
    print(f"   Unique contacts after merge: {len(merged_contacts)}")
    print(f"   Deduplication rate: {((total_contacts - len(merged_contacts))/total_contacts*100):.1f}%" if total_contacts > 0 else "   Deduplication rate: 0%")
    
    # Apply enhanced scoring
    if scorer and merged_contacts:
        print(f"\n[TARGET] APPLYING ENHANCED SCORING:")
        print("-" * 30)
        
        try:
            # Batch score all contacts
            scores = await scorer.score_contacts_batch(merged_contacts)
            
            # Generate scoring insights
            insights = scorer.generate_enhanced_scoring_insights(merged_contacts)
            
            print(f"[OK] Scored {len(scores)} contacts successfully")
            print(f"📈 Average score: {insights['average_score']:.2f}")
            print(f"[TOP] High-value contacts: {insights['score_distribution']['high_value']}")
            print(f"🔗 Social media coverage: {insights['social_media_coverage']['total_with_social']} contacts")
            print(f"🤖 AI analysis coverage: {insights['ai_analysis_coverage']['sentiment_analysis']} contacts")
            
            # Show AI/API availability
            ai_engines = insights['ai_analysis_coverage']['ai_engines_available']
            enrichment_sources = insights['enrichment_sources']
            
            print(f"\n[CONFIG] ACTIVE INTEGRATIONS:")
            print(f"   HuggingFace NLP: {'[OK]' if ai_engines['huggingface'] else '[FAIL]'}")
            print(f"   OpenAI Analysis: {'[OK]' if ai_engines['openai'] else '[FAIL]'}")
            print(f"   Clearbit API: {'[OK]' if enrichment_sources['clearbit_available'] else '[FAIL]'}")
            print(f"   Hunter.io API: {'[OK]' if enrichment_sources['hunter_available'] else '[FAIL]'}")
            print(f"   People Data Labs: {'[OK]' if enrichment_sources['pdl_available'] else '[FAIL]'}")
            
        except Exception as e:
            print(f"⚠️ Enhanced scoring failed: {e}")
            print("📝 Contacts extracted without enhanced scoring")
    
    return merged_contacts, all_contacts, scorer

async def enrich_contacts_with_apis(contacts, enricher):
    """Enrich contacts using available APIs"""
    if not contacts or not enricher:
        return contacts
    
    print(f"\n🔍 ENRICHING {len(contacts)} CONTACTS:")
    print("-" * 35)
    
    try:
        enriched_contacts = await enricher.enrich_contacts(contacts)
        
        # Count enrichment success
        enriched_count = sum(1 for c in enriched_contacts if c.data_sources)
        enrichment_rate = (enriched_count / len(contacts)) * 100 if contacts else 0
        
        print(f"[OK] Enrichment completed")
        print(f"[STATS] {enriched_count}/{len(contacts)} contacts enriched ({enrichment_rate:.1f}%)")
        
        # Show enrichment sources used
        sources_used = set()
        for contact in enriched_contacts:
            sources_used.update(contact.data_sources)
        
        if sources_used:
            print(f"[CONFIG] Sources used: {', '.join(sources_used)}")
        
        return enriched_contacts
        
    except Exception as e:
        print(f"⚠️ Enrichment failed: {e}")
        print("📝 Continuing with basic contact data...")
        return contacts

async def generate_comprehensive_report(contacts, scorer, output_format="console"):
    """Generate comprehensive contact analysis report"""
    
    if not contacts:
        print("[FAIL] No contacts to analyze")
        return
    
    print(f"\n📋 COMPREHENSIVE CONTACT ANALYSIS:")
    print("=" * 45)
    
    # Overall statistics
    total_contacts = len(contacts)
    total_interactions = sum(c.frequency for c in contacts)
    avg_interactions = total_interactions / total_contacts if total_contacts > 0 else 0
    
    print(f"\n[STATS] OVERALL STATISTICS:")
    print(f"   Total Contacts: {total_contacts:,}")
    print(f"   Total Interactions: {total_interactions:,}")
    print(f"   Average Interactions/Contact: {avg_interactions:.1f}")
    
    # Score distribution (if scorer available)
    if scorer:
        try:
            insights = scorer.generate_enhanced_scoring_insights(contacts)
            
            print(f"\n[TARGET] SCORING ANALYSIS:")
            score_dist = insights['score_distribution']
            print(f"   High-Value Contacts (≥0.8): {score_dist['high_value']} ({score_dist['high_value']/total_contacts*100:.1f}%)")
            print(f"   Medium-Value Contacts (0.5-0.8): {score_dist['medium_value']} ({score_dist['medium_value']/total_contacts*100:.1f}%)")
            print(f"   Low-Value Contacts (<0.5): {score_dist['low_value']} ({score_dist['low_value']/total_contacts*100:.1f}%)")
            print(f"   Average Score: {insights['average_score']:.2f}/1.0")
            
            # Deal potential analysis
            deal_analysis = insights['deal_potential_analysis']
            print(f"\n💰 DEAL POTENTIAL ANALYSIS:")
            print(f"   High-Potential Contacts: {deal_analysis['high_potential_contacts']} ({deal_analysis['percentage_high_potential']:.1f}%)")
            print(f"   Average Deal Potential: {deal_analysis['average_deal_potential']:.2f}/1.0")
            
            # Social media analysis
            social_coverage = insights['social_media_coverage']
            print(f"\n🌐 SOCIAL MEDIA COVERAGE:")
            print(f"   LinkedIn Profiles: {social_coverage['linkedin']} ({social_coverage['linkedin']/total_contacts*100:.1f}%)")
            print(f"   Twitter Profiles: {social_coverage['twitter']} ({social_coverage['twitter']/total_contacts*100:.1f}%)")
            print(f"   GitHub Profiles: {social_coverage['github']} ({social_coverage['github']/total_contacts*100:.1f}%)")
            print(f"   Total with Social: {social_coverage['total_with_social']} ({social_coverage['total_with_social']/total_contacts*100:.1f}%)")
            
        except Exception as e:
            print(f"⚠️ Scoring analysis failed: {e}")
    
    # Industry distribution
    industry_dist = defaultdict(int)
    for contact in contacts:
        industry = contact.industry or 'Unknown'
        industry_dist[industry] += 1
    
    print(f"\n🏢 INDUSTRY DISTRIBUTION:")
    sorted_industries = sorted(industry_dist.items(), key=lambda x: x[1], reverse=True)
    for industry, count in sorted_industries[:10]:  # Top 10 industries
        percentage = (count / total_contacts) * 100
        print(f"   {industry}: {count} ({percentage:.1f}%)")
    
    # Company analysis
    company_dist = defaultdict(int)
    for contact in contacts:
        company = contact.company or 'Unknown'
        company_dist[company] += 1
    
    print(f"\n🏢 TOP COMPANIES:")
    sorted_companies = sorted(company_dist.items(), key=lambda x: x[1], reverse=True)
    for company, count in sorted_companies[:10]:  # Top 10 companies
        percentage = (count / total_contacts) * 100
        print(f"   {company}: {count} ({percentage:.1f}%)")
    
    # Communication patterns
    bidirectional_contacts = sum(1 for c in contacts if c.sent_to > 0 and c.received_from > 0)
    meeting_contacts = sum(1 for c in contacts if c.meeting_count > 0)
    recent_contacts = sum(1 for c in contacts if (datetime.now() - c.last_seen).days <= 30)
    
    print(f"\n💬 COMMUNICATION PATTERNS:")
    print(f"   Bidirectional Communication: {bidirectional_contacts} ({bidirectional_contacts/total_contacts*100:.1f}%)")
    print(f"   Have Had Meetings: {meeting_contacts} ({meeting_contacts/total_contacts*100:.1f}%)")
    print(f"   Recent Contact (30 days): {recent_contacts} ({recent_contacts/total_contacts*100:.1f}%)")
    
    # Data quality analysis
    with_location = sum(1 for c in contacts if c.location)
    with_title = sum(1 for c in contacts if c.job_title)
    with_company = sum(1 for c in contacts if c.company)
    enriched_contacts = sum(1 for c in contacts if c.data_sources)
    
    print(f"\n[STATS] DATA QUALITY:")
    print(f"   With Location: {with_location} ({with_location/total_contacts*100:.1f}%)")
    print(f"   With Job Title: {with_title} ({with_title/total_contacts*100:.1f}%)")
    print(f"   With Company: {with_company} ({with_company/total_contacts*100:.1f}%)")
    print(f"   API Enriched: {enriched_contacts} ({enriched_contacts/total_contacts*100:.1f}%)")

async def show_top_contacts_detailed(contacts, scorer=None, count=10):
    """Show detailed view of top contacts"""
    
    print(f"\n[TOP] TOP {count} CONTACTS (DETAILED VIEW):")
    print("=" * 60)
    
    # Sort contacts by score if scorer available, otherwise by interaction count
    if scorer:
        try:
            ranked_contacts = scorer.rank_contacts_by_score(contacts, 'overall')
            top_contacts = [contact for contact, score in ranked_contacts[:count]]
        except Exception as e:
            print(f"⚠️ Scoring failed, using interaction count: {e}")
            top_contacts = sorted(contacts, key=lambda c: c.frequency, reverse=True)[:count]
    else:
        top_contacts = sorted(contacts, key=lambda c: c.frequency, reverse=True)[:count]
    
    for i, contact in enumerate(top_contacts, 1):
        # Get contact score if available
        overall_score = "N/A"
        deal_potential = "N/A"
        social_influence = "N/A"
        
        if scorer and hasattr(contact, 'contact_score') and contact.contact_score:
            score = contact.contact_score
            overall_score = f"{score.overall_score:.2f}"
            deal_potential = f"{score.deal_potential:.1%}"
            social_influence = f"{score.scoring_factors.get('social_influence', 0):.2f}"
        
        # Basic contact info
        relationship_strength = contact.calculate_relationship_strength()
        # days_since_last = (datetime.now() - contact.last_seen).days
        days_since_last = safe_datetime_diff(contact.last_seen)
        
        print(f"\n{i:2d}. {contact.name or 'Unknown Name'}")
        print(f"    [EMAIL] {contact.email}")
        print(f"    🏢 {contact.company or 'Unknown Company'}")
        print(f"    💼 {contact.job_title or 'Unknown Title'}")
        print(f"    📍 {contact.location or 'Unknown Location'}")
        print(f"    💰 {contact.estimated_net_worth or 'Unknown'}")
        
        print(f"    [STATS] Interactions: {contact.frequency} | Strength: {relationship_strength:.1%} | Last: {days_since_last}d ago")
        print(f"    [TARGET] Score: {overall_score} | Deal Potential: {deal_potential} | Social: {social_influence}")
        
        # Social profiles
        if contact.social_profiles:
            social_str = []
            for profile in contact.social_profiles:
                social_str.append(f"{profile.platform}")
            print(f"    🌐 Social: {', '.join(social_str)}")
        
        # Data sources
        if contact.data_sources:
            print(f"    🔍 Sources: {', '.join(contact.data_sources)}")
        
        # Account sources
        if hasattr(contact, 'source_accounts') and contact.source_accounts:
            print(f"    [EMAIL] Found in: {', '.join(contact.source_accounts)}")

async def export_enhanced_data(contacts, export_format, filename=None, include_analytics=True):
    """Export with enhanced data and analytics"""
    
    print(f"\n📤 EXPORTING TO {export_format.upper()}:")
    print("-" * 35)
    
    try:
        if export_format == "excel" and EXCEL_EXPORT_AVAILABLE:
            exporter = EnhancedExcelExporter()
            
            if include_analytics:
                # Create comprehensive analytics dashboard
                export_path = await exporter.export_analytics_dashboard(contacts)
                print(f"[OK] Analytics dashboard exported: {export_path}")
            else:
                # Standard export with analytics
                export_path = await exporter.export_contacts(
                    contacts=contacts,
                    filename=filename,
                    include_analytics=True,
                    include_charts=True
                )
                print(f"[OK] Excel export completed: {export_path}")
            
            return export_path
        
        elif export_format == "excel" and not EXCEL_EXPORT_AVAILABLE:
            print("[FAIL] Excel export requested but module not available")
            print("💡 Install dependencies: pip install openpyxl pandas")
            # Fall back to CSV
            export_path = await export_to_enhanced_csv(contacts, filename)
            print(f"[OK] Exported as CSV instead: {export_path}")
            return export_path
        
        elif export_format == "csv":
            export_path = await export_to_enhanced_csv(contacts, filename)
            print(f"[OK] CSV export completed: {export_path}")
            return export_path
        
        elif export_format == "json":
            export_path = await export_to_enhanced_json(contacts, filename)
            print(f"[OK] JSON export completed: {export_path}")
            return export_path
    
    except Exception as e:
        print(f"[FAIL] Export failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def export_to_enhanced_csv(contacts, filename=None):
    """Export to CSV with enhanced scoring data"""
    try:
        import pandas as pd
        
        # Convert contacts to enhanced DataFrame
        data = []
        for contact in contacts:
            # Get scoring data if available
            scoring_data = {}
            if hasattr(contact, 'contact_score') and contact.contact_score:
                score = contact.contact_score
                scoring_data = {
                    'Overall_Score': f"{score.overall_score:.3f}",
                    'Deal_Potential': f"{score.deal_potential:.1%}",
                    'Influence_Score': f"{score.influence_score:.1%}",
                    'Social_Influence': score.scoring_factors.get('social_influence', 0),
                    'Response_Likelihood': f"{score.response_likelihood:.1%}",
                    'Sentiment_Score': score.scoring_factors.get('sentiment', 0),
                    'Company_Importance': score.scoring_factors.get('company_importance', 0),
                    'Title_Seniority': score.scoring_factors.get('title_seniority', 0),
                    'AI_Sentiment_Available': 'Yes' if score.scoring_factors.get('ai_sentiment_available') else 'No',
                    'LinkedIn_Connections': score.scoring_factors.get('linkedin_connections', 'Unknown'),
                    'Twitter_Followers': score.scoring_factors.get('twitter_followers', 'Unknown')
                }
            
            # Basic contact data
            row = {
                'Name': contact.name,
                'Email': contact.email,
                'Company': contact.company or '',
                'Job_Title': contact.job_title or '',
                'Industry': contact.industry or '',
                'Location': contact.location or '',
                'Net_Worth': contact.estimated_net_worth or '',
                'Provider': contact.provider.value if contact.provider else '',
                'Source_Accounts': ', '.join(getattr(contact, 'source_accounts', [])),
                'Frequency': contact.frequency,
                'Sent_To': contact.sent_to,
                'Received_From': contact.received_from,
                'Meeting_Count': contact.meeting_count,
                'Relationship_Strength': f"{contact.calculate_relationship_strength():.1%}",
                'Days_Since_Last_Contact': safe_datetime_diff(contact.last_seen),
                'Social_Profiles': len(contact.social_profiles),
                'Data_Sources': ', '.join(contact.data_sources),
                'Confidence': contact.confidence,
                'First_Seen': contact.first_seen.isoformat() if contact.first_seen else '',
                'Last_Seen': contact.last_seen.isoformat() if contact.last_seen else '',
                **scoring_data  # Add all scoring data
            }
            
            data.append(row)
        
        df = pd.DataFrame(data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = filename or f"enhanced_contacts_{timestamp}.csv"
        
        # Ensure exports directory exists
        exports_dir = Path("exports")
        exports_dir.mkdir(exist_ok=True)
        csv_path = exports_dir / csv_filename
        
        df.to_csv(csv_path, index=False)
        return str(csv_path)
    
    except ImportError:
        print("[FAIL] pandas not available for CSV export")
        return None

async def export_to_enhanced_json(contacts, filename=None):
    """Export to JSON with enhanced scoring data"""
    
    # Convert contacts to enhanced JSON
    data = []
    for contact in contacts:
        # Get scoring data if available
        scoring_data = {}
        if hasattr(contact, 'contact_score') and contact.contact_score:
            score = contact.contact_score
            scoring_data = {
                'overall_score': score.overall_score,
                'deal_potential': score.deal_potential,
                'influence_score': score.influence_score,
                'response_likelihood': score.response_likelihood,
                'engagement_score': score.engagement_score,
                'importance_score': score.importance_score,
                'scoring_factors': score.scoring_factors,
                'sentiment_trend': score.sentiment_trend,
                'preferred_communication': score.preferred_communication,
                'best_contact_time': score.best_contact_time
            }
        
        contact_data = {
            'name': contact.name,
            'email': contact.email,
            'company': contact.company or '',
            'job_title': contact.job_title or '',
            'industry': contact.industry or '',
            'location': contact.location or '',
            'estimated_net_worth': contact.estimated_net_worth or '',
            'provider': contact.provider.value if contact.provider else '',
            'source_accounts': getattr(contact, 'source_accounts', []),
            'frequency': contact.frequency,
            'sent_to': contact.sent_to,
            'received_from': contact.received_from,
            'meeting_count': contact.meeting_count,
            'relationship_strength': contact.calculate_relationship_strength(),
            'days_since_last_contact': (datetime.now() - contact.last_seen).days,
            'social_profiles': [
                {
                    'platform': profile.platform,
                    'url': profile.url,
                    'username': profile.username,
                    'followers': getattr(profile, 'followers', 0)
                } for profile in contact.social_profiles
            ],
            'data_sources': contact.data_sources,
            'confidence': contact.confidence,
            'first_seen': contact.first_seen.isoformat() if contact.first_seen else '',
            'last_seen': contact.last_seen.isoformat() if contact.last_seen else '',
            'enhanced_scoring': scoring_data  # Add all enhanced scoring data
        }
        
        # Add interactions if available
        if hasattr(contact, 'interactions') and contact.interactions:
            contact_data['recent_interactions'] = []
            for interaction in contact.interactions[-5:]:  # Last 5 interactions
                interaction_data = {
                    'type': interaction.type.value if hasattr(interaction.type, 'value') else str(interaction.type),
                    'timestamp': interaction.timestamp.isoformat() if interaction.timestamp else '',
                    'subject': getattr(interaction, 'subject', ''),
                    'direction': getattr(interaction, 'direction', ''),
                    'source_account': getattr(interaction, 'source_account', ''),
                    'content_preview': getattr(interaction, 'content_preview', '')[:100]  # First 100 chars
                }
                contact_data['recent_interactions'].append(interaction_data)
        
        data.append(contact_data)
    
    # Create comprehensive export with metadata
    export_data = {
        'export_info': {
            'timestamp': datetime.now().isoformat(),
            'total_contacts': len(contacts),
            'export_type': 'enhanced_contact_export',
            'version': '2.1.0',
            'features': {
                'enhanced_scoring': ENHANCED_SCORING_AVAILABLE,
                'enrichment': ENRICHMENT_AVAILABLE,
                'social_media_analysis': True,
                'ai_sentiment_analysis': True,
                'multi_account_support': True
            }
        },
        'summary': {
            'providers': list(set(c.provider.value if c.provider else 'Unknown' for c in contacts)),
            'source_accounts': list(set().union(*[getattr(c, 'source_accounts', []) for c in contacts])),
            'industries': list(set(c.industry for c in contacts if c.industry)),
            'companies': list(set(c.company for c in contacts if c.company))[:20],  # Top 20 companies
            'data_sources': list(set().union(*[c.data_sources for c in contacts])),
            'social_platforms': list(set().union(*[[p.platform for p in c.social_profiles] for c in contacts]))
        },
        'contacts': data
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = filename or f"enhanced_contacts_{timestamp}.json"
    
    # Ensure exports directory exists
    exports_dir = Path("exports")
    exports_dir.mkdir(exist_ok=True)
    json_path = exports_dir / json_filename
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    return str(json_path)

async def main():
    """Enhanced main function with comprehensive AI and API integration"""
    
    parser = argparse.ArgumentParser(description="Enhanced Email Enrichment System - AI & API Integration")
    
    # Status and configuration commands
    parser.add_argument("--status", action="store_true", help="Show comprehensive system status")
    parser.add_argument("--test-ai", action="store_true", help="Test AI components (HuggingFace, OpenAI)")
    parser.add_argument("--test-apis", action="store_true", help="Test enrichment APIs")
    
    # Account management
    parser.add_argument("--list-accounts", action="store_true", help="List all available accounts")
    parser.add_argument("--test-accounts", action="store_true", help="Test all account connections")
    
    # Extraction and processing
    parser.add_argument("--extract", action="store_true", help="Extract and score contacts")
    parser.add_argument("--providers", nargs="+", help="Specify providers (gmail, outlook, yahoo, icloud)")
    parser.add_argument("--days-back", type=int, default=30, help="Days to look back for emails")
    parser.add_argument("--max-emails", type=int, default=1000, help="Maximum emails per account")
    
    # Enhanced features
    parser.add_argument("--enhanced-scoring", action="store_true", default=True, help="Use enhanced AI scoring (default: True)")
    parser.add_argument("--basic-scoring", action="store_true", help="Use basic scoring only")
    parser.add_argument("--enrich", action="store_true", help="Enrich contacts with API data")
    parser.add_argument("--detailed-report", action="store_true", help="Generate detailed analysis report")
    
    # Export options
    parser.add_argument("--export-format", choices=["excel", "csv", "json"], help="Export format")
    parser.add_argument("--output-file", help="Output file name")
    parser.add_argument("--analytics", action="store_true", help="Include comprehensive analytics")
    
    # Analysis options
    parser.add_argument("--top-contacts", type=int, default=10, help="Number of top contacts to show")
    parser.add_argument("--score-type", choices=["overall", "deal_potential", "influence", "social_influence"], 
                        default="overall", help="Scoring type for rankings")
    
    args = parser.parse_args()
    
    # Create factory
    factory = get_provider_factory()
    
    # Handle status command
    if args.status:
        print("[START] ENHANCED EMAIL ENRICHMENT SYSTEM")
        print("=" * 70)
        print(f"🏷️  Version: 2.1.0 (Enhanced AI & API Integration)")
        print(f"🌍 Environment: Production-Ready")
        print(f"📁 Working Directory: {os.getcwd()}")
        print(f"🐍 Python Version: {sys.version.split()[0]}")
        
        check_all_provider_status()
        return
    
    # Handle AI testing
    if args.test_ai:
        print("🤖 TESTING AI COMPONENTS:")
        print("=" * 30)
        
        # Test HuggingFace
        if check_huggingface_availability():
            try:
                from ai.huggingface_nlp import HuggingFaceNLPEngine
                nlp_engine = HuggingFaceNLPEngine()
                if nlp_engine.enabled:
                    print("[OK] HuggingFace NLP: AVAILABLE")
                    
                    # Test sentiment analysis
                    test_result = await nlp_engine.analyze_sentiment("This is a great opportunity for collaboration!")
                    if test_result:
                        print(f"   [STATS] Sentiment Test: {test_result}")
                    else:
                        print("   ⚠️ Sentiment analysis not working")
                else:
                    print("[FAIL] HuggingFace NLP: DISABLED")
            except Exception as e:
                print(f"[FAIL] HuggingFace NLP: ERROR - {e}")
        else:
            print("[FAIL] HuggingFace NLP: NOT AVAILABLE (missing dependencies)")
        
        # Test OpenAI
        if os.getenv('OPENAI_API_KEY'):
            try:
                from ai.openai_analyzer import OpenAIEmailAnalyzer
                openai_analyzer = OpenAIEmailAnalyzer()
                if openai_analyzer.enabled:
                    print("[OK] OpenAI Analysis: AVAILABLE")
                else:
                    print("[FAIL] OpenAI Analysis: DISABLED")
            except Exception as e:
                print(f"[FAIL] OpenAI Analysis: ERROR - {e}")
        else:
            print("[FAIL] OpenAI Analysis: NO API KEY")
        
        # Test Enhanced Scoring
        if ENHANCED_SCORING_AVAILABLE:
            try:
                scorer = EnhancedContactScoringEngine()
                print("[OK] Enhanced Scoring: AVAILABLE")
                print(f"   [CONFIG] AI Engines: HF={scorer.nlp_engine is not None}, OpenAI={scorer.openai_analyzer is not None}")
                print(f"   [CONFIG] APIs: Clearbit={scorer.clearbit_source is not None}, Hunter={scorer.hunter_source is not None}, PDL={scorer.pdl_source is not None}")
            except Exception as e:
                print(f"[FAIL] Enhanced Scoring: ERROR - {e}")
        else:
            print("[FAIL] Enhanced Scoring: NOT AVAILABLE")
        
        return
    
    # Handle API testing
    if args.test_apis:
        print("🔍 TESTING ENRICHMENT APIS:")
        print("=" * 35)
        
        apis_to_test = [
            ("Clearbit", "CLEARBIT_API_KEY"),
            ("Hunter.io", "HUNTER_API_KEY"),
            ("People Data Labs", "PDL_API_KEY"),
            ("Apollo.io", "APOLLO_API_KEY"),
            ("ZoomInfo", "ZOOMINFO_API_KEY")
        ]
        
        for api_name, env_var in apis_to_test:
            if os.getenv(env_var):
                print(f"[OK] {api_name}: API KEY CONFIGURED")
                # Here you could add actual API testing
            else:
                print(f"[FAIL] {api_name}: NO API KEY")
        
        return
    
    # Handle account listing and testing
    if args.list_accounts:
        configs = factory.load_provider_configs()
        if not configs:
            print("[FAIL] No accounts configured")
            return
        
        print("[EMAIL] AVAILABLE EMAIL ACCOUNTS:")
        print("=" * 40)
        
        total_accounts = 0
        for provider_name, config in configs.items():
            accounts = config.get('accounts', [])
            print(f"\n[EMAIL] {provider_name.upper()}:")
            
            if accounts:
                for account in accounts:
                    display = account if account != "primary" else f"primary ({config.get('email', 'configured')})"
                    print(f"   • {display}")
                    total_accounts += 1
            else:
                print("   [FAIL] No accounts found")
        
        print(f"\n[STATS] Total accounts available: {total_accounts}")
        return
    
    if args.test_accounts:
        try:
            providers = await factory.get_all_available_providers()
        except Exception as e:
            print(f"[FAIL] Failed to get providers: {e}")
            return
        
        if not providers:
            print("[FAIL] No providers available for testing")
            return
        
        # Filter providers if specified
        if args.providers:
            filtered_providers = {name: providers[name] for name in args.providers if name in providers}
            providers = filtered_providers
        
        print("🧪 TESTING EMAIL ACCOUNT CONNECTIONS:")
        print("=" * 50)
        
        test_results = await factory.test_all_providers(providers)
        
        total_tested = 0
        successful_tests = 0
        
        for provider_name, results in test_results.items():
            print(f"\n[EMAIL] {provider_name.upper()}:")
            
            for result in results:
                total_tested += 1
                email = result.get('email', 'Unknown')
                success = result.get('success', False)
                processing_time = result.get('processing_time', 0)
                
                if success:
                    successful_tests += 1
                    print(f"   [OK] {email}: CONNECTED ({processing_time:.2f}s)")
                else:
                    error = result.get('error', 'Unknown error')
                    print(f"   [FAIL] {email}: FAILED - {error}")
        
        print(f"\n[STATS] TEST SUMMARY:")
        print(f"   Total accounts tested: {total_tested}")
        print(f"   Successful connections: {successful_tests}")
        print(f"   Success rate: {(successful_tests/total_tested*100):.1f}%" if total_tested > 0 else "   Success rate: 0%")
        
        await factory.cleanup_all_providers()
        return
    
    # Handle main extraction and analysis
    if args.extract or args.export_format:
        # Check if any providers are configured
        configs = factory.load_provider_configs()
        if not configs:
            print("[FAIL] No providers configured")
            print("💡 Run --status to see setup options")
            return
        
        # Determine scoring method
        use_enhanced = args.enhanced_scoring and not args.basic_scoring and ENHANCED_SCORING_AVAILABLE
        
        # Extract and score contacts
        merged_contacts, raw_contacts, scorer = await extract_and_score_contacts(
            factory, 
            args.providers, 
            args.days_back, 
            args.max_emails,
            use_enhanced
        )
        
        if not merged_contacts:
            print("[FAIL] No contacts found")
            await factory.cleanup_all_providers()
            return
        
        # Enrich contacts if requested
        if args.enrich and ENRICHMENT_AVAILABLE:
            enricher = ContactEnricher()
            try:
                merged_contacts = await enrich_contacts_with_apis(merged_contacts, enricher)
            except Exception as e:
                print(f"⚠️ Enrichment failed: {e}")
            finally:
                await enricher.cleanup()
        elif args.enrich and not ENRICHMENT_AVAILABLE:
            print("⚠️ Enrichment requested but module not available")
        
        # Re-score contacts if they were enriched and we have enhanced scoring
        if args.enrich and scorer and merged_contacts:
            print(f"\n🔄 RE-SCORING AFTER ENRICHMENT:")
            try:
                await scorer.score_contacts_batch(merged_contacts)
                print("[OK] Contacts re-scored with enriched data")
            except Exception as e:
                print(f"⚠️ Re-scoring failed: {e}")
        
        # Generate detailed report if requested
        if args.detailed_report:
            await generate_comprehensive_report(merged_contacts, scorer)
        
        # Show top contacts
        await show_top_contacts_detailed(merged_contacts, scorer, args.top_contacts)
        
        # Export if format specified
        if args.export_format:
            export_path = await export_enhanced_data(
                merged_contacts, 
                args.export_format, 
                args.output_file,
                args.analytics
            )
            
            if export_path:
                print(f"\n📋 EXPORT SUMMARY:")
                print(f"   📁 File: {export_path}")
                print(f"   [STATS] Contacts: {len(merged_contacts)}")
                print(f"   [TARGET] Enhanced Scoring: {'Yes' if scorer else 'No'}")
                print(f"   🔍 API Enrichment: {'Yes' if args.enrich else 'No'}")
                print(f"   📈 Analytics: {'Yes' if args.analytics else 'No'}")
        
        # Show scoring insights if available
        if scorer and not args.export_format:
            try:
                insights = scorer.generate_enhanced_scoring_insights(merged_contacts)
                
                print(f"\n[TARGET] ENHANCED SCORING INSIGHTS:")
                print("=" * 40)
                print(f"   Average Score: {insights['average_score']:.2f}/1.0")
                print(f"   High-Value Contacts: {insights['score_distribution']['high_value']}")
                print(f"   Deal Potential (High): {insights['deal_potential_analysis']['high_potential_contacts']}")
                print(f"   Social Media Coverage: {insights['social_media_coverage']['total_with_social']}/{len(merged_contacts)}")
                print(f"   AI Analysis Coverage: {insights['ai_analysis_coverage']['sentiment_analysis']}/{len(merged_contacts)}")
                
                # Show top companies by average score
                if insights['top_companies']:
                    print(f"\n🏢 TOP COMPANIES BY SCORE:")
                    for company, avg_score, contact_count in insights['top_companies'][:5]:
                        print(f"   {company}: {avg_score:.2f} avg ({contact_count} contacts)")
                
            except Exception as e:
                print(f"⚠️ Scoring insights failed: {e}")
        
        # Cleanup
        await factory.cleanup_all_providers()
        return
    
    # Default help message with enhanced options
    print("[START] ENHANCED EMAIL ENRICHMENT SYSTEM")
    print("=" * 70)
    print("Version 2.1.0 - AI & API Integration")
    print("\n🔍 Status & Testing:")
    print("  --status                    Show comprehensive system status")
    print("  --test-ai                   Test AI components (HuggingFace, OpenAI)")
    print("  --test-apis                 Test enrichment API connections")
    print("  --list-accounts             List all available email accounts")
    print("  --test-accounts             Test email account connections")
    print("\n[EMAIL] Contact Extraction & Analysis:")
    print("  --extract                   Extract and analyze contacts")
    print("  --providers gmail outlook   Specify provider(s) to use")
    print("  --days-back 60              Look back N days (default: 30)")
    print("  --max-emails 2000           Max emails per account (default: 1000)")
    print("\n[TARGET] Enhanced Features:")
    print("  --enhanced-scoring          Use AI-powered scoring (default: ON)")
    print("  --basic-scoring             Use basic scoring only")
    print("  --enrich                    Enrich with API data (Clearbit, Hunter, PDL)")
    print("  --detailed-report           Generate comprehensive analysis report")
    print("  --top-contacts 20           Number of top contacts to show (default: 10)")
    print("\n[STATS] Export & Analytics:")
    print("  --export-format excel       Export format (excel/csv/json)")
    print("  --analytics                 Include comprehensive analytics")
    print("  --output-file name          Custom output filename")
    print("  --score-type deal_potential Ranking type (overall/deal_potential/influence)")
    print("\n💡 Usage Examples:")
    print("  # Check system status and configuration")
    print("  python main.py --status")
    print("\n  # Test AI and API components")
    print("  python main.py --test-ai --test-apis")
    print("\n  # Extract with enhanced AI scoring and API enrichment")
    print("  python main.py --extract --enhanced-scoring --enrich")
    print("\n  # Extract from specific providers with detailed analysis")
    print("  python main.py --extract --providers gmail outlook --detailed-report")
    print("\n  # Export to Excel with comprehensive analytics")
    print("  python main.py --extract --export-format excel --analytics")
    print("\n  # Advanced: Full pipeline with all features")
    print("  python main.py --extract --enhanced-scoring --enrich --detailed-report \\")
    print("                 --export-format excel --analytics --top-contacts 25")
    print("\n[CONFIG] Features Available:")
    features = [
        ("Enhanced AI Scoring", ENHANCED_SCORING_AVAILABLE),
        ("API Enrichment", ENRICHMENT_AVAILABLE),
        ("Excel Export", EXCEL_EXPORT_AVAILABLE),
        ("HuggingFace NLP", check_huggingface_availability()),
        ("OpenAI Analysis", bool(os.getenv('OPENAI_API_KEY'))),
        ("Multi-Account Support", True)
    ]
    
    for feature, available in features:
        status = "[OK] Available" if available else "[FAIL] Limited"
        print(f"  {feature}: {status}")

if __name__ == "__main__":
    asyncio.run(main())


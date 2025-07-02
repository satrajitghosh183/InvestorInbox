# InvestorInbox
AI-driven email enrichment &amp; outreach platform for investor fundraising pipelines.
# Email Enrichment System

A production-ready CLI application that connects to multiple email providers (Gmail, Outlook, Yahoo/IMAP), extracts contact metadata from emails, enriches contact profiles via AI and public APIs, and exports results in Excel, CSV, or JSON formats. Ideal for sales, networking, and relationship analytics.

## Features

* **Multi-Provider Support**: Gmail (Google API), Outlook (Microsoft Graph), Yahoo/IMAP, POP3
* **Contact Extraction**: Parses `From`, `To`, `Cc`, `Bcc` headers to build contact list
* **Enrichment**: Augments contacts with location, net worth, job title, company, social profiles, and AI-driven insights
* **Export Options**: Excel (with analytics dashboard and charts), CSV, JSON
* **Logging**: Structured logs to console and `logs/email_enrichment.log`
* **Mock Mode**: Fallback providers for testing without real credentials

## Prerequisites

* Python 3.8 or higher
* Git
* (Optional) Google API credentials file for Gmail
* (Optional) Environment variables for Outlook and Yahoo credentials

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-org/email-enrichment.git
   cd email-enrichment
   ```
2. **Create and activate a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Gmail**

   * Download OAuth credentials JSON from Google Cloud Console
   * Save as `config/gmail_credentials.json`
2. **Outlook**

   ```bash
   export OUTLOOK_CLIENT_ID=<your_client_id>
   export OUTLOOK_CLIENT_SECRET=<your_client_secret>
   export OUTLOOK_TENANT_ID=<your_tenant_id>  # optional, defaults to 'common'
   ```
3. **Yahoo/IMAP**

   ```bash
   export YAHOO_EMAIL=<your_email>
   export YAHOO_APP_PASSWORD=<your_app_password>
   ```
4. **Directory structure**

   ```text
   ├── config/               # credentials files
   │   ├── gmail_credentials.json
   ├── data/tokens/          # OAuth tokens persisted here
   ├── logs/                 # log files
   ├── exports/              # generated CSV/Excel/JSON outputs
   ├── src/                  # source code
   │   ├── main.py
   │   ├── utils/
   │   ├── core/
   │   ├── providers/
   │   ├── enrichment/
   │   └── exporters/
   └── requirements.txt
   ```

## Usage

From project root, run:

```bash
python src/main.py [OPTIONS]
```

### Common Commands

* **Show configuration summary**

  ```bash
  python src/main.py --config-summary
  ```

* **List available providers**

  ```bash
  python src/main.py --list-providers
  ```

* **Setup/test provider authentication**

  ```bash
  python src/main.py --setup-providers
  ```

* **Extract sample contacts**

  ```bash
  python src/main.py --test --providers gmail outlook
  ```

### Exporting Contacts

* **Export to Excel**

  ```bash
  python src/main.py --test --export-format excel --output-file contacts.xlsx
  ```

* **Export with enrichment**

  ```bash
  python src/main.py --test --export-format excel --enrich --analytics
  ```

* **Export to CSV**

  ```bash
  python src/main.py --test --export-format csv --output-file contacts.csv
  ```

* **Export to JSON**

  ```bash
  python src/main.py --test --export-format json --output-file contacts.json
  ```

## Detailed Run Flow

1. **Load provider configs** from `config/` and environment
2. **Authenticate** each provider (OAuth or IMAP/POP3 login)
3. **Extract contacts** from emails within `--days-back` (default 30 days)
4. **Merge & deduplicate** contacts across providers
5. **Enrich** (if `--enrich`): call AI/APIs to augment contact data
6. **Export** (if `--export-format`): save to desired format with analytics
7. **Cleanup**: close provider sessions and exit

## Troubleshooting

* **No providers configured**: ensure credentials are placed in `config/` and env vars set
* **Gmail OAuth errors**: delete `data/tokens/gmail_token.json` and re-run `--setup-providers`
* **Rate limits**: monitor `rate_limit_remaining` in logs; adjust `max_emails`

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/foo`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to remote branch (`git push origin feature/foo`)
5. Open a pull request


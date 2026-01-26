# Profile Enricher - Quick Start Guide

## What You Need

1. A CSV file with LinkedIn profile URLs
2. Column name containing the URLs (default: "Profile URL")
3. LinkedIn credentials configured in `.env`

## Step-by-Step

### 1. Prepare Your CSV File

Create a CSV file with at least one column containing LinkedIn profile URLs:

```csv
Profile URL,Name,Company
https://www.linkedin.com/in/john-doe/,John Doe,Example Corp
https://www.linkedin.com/in/jane-smith/,Jane Smith,Tech Inc
```

**Important**: The column name can be anything, but you'll need to know it when running the script.

### 2. Run the Script

```bash
python cli.py
```

### 3. Select Profile Enricher

When prompted, select option **7**:
```
What would you like to do?
1. Scrape LinkedIn group members
2. Send messages to group members
3. Scrape profiles from LinkedIn search
4. Send a single connection request
5. Send mass connection requests from CSV
6. Scrape LinkedIn profiles using Google search
7. Enrich LinkedIn profiles from CSV (Extract emails)

Enter your choice (1 - 7): 7
```

### 4. Provide Inputs

**CSV File Path**:
```
Enter the CSV file path: data/csv/my_profiles.csv
```

**Column Name** (press Enter to use default "Profile URL"):
```
Enter the column name for LinkedIn URLs (default: 'Profile URL'): [Enter]
```

**Max Profiles** (press Enter to process all):
```
Maximum profiles to process (press Enter for all): 5
```

### 5. Wait for Completion

The script will:
- Visit each LinkedIn profile
- Extract name and experience information
- Search Google for company domains
- Generate email addresses
- Save results incrementally

**Example Console Output**:
```
============================================================
🚀 PROFILE ENRICHER - Starting
============================================================

📂 Reading input CSV: data/csv/profiles.csv
✓ Found 3 profiles to enrich
📊 Processing first 3 profiles
📝 Output file: data/csv/profiles_enriched_20260104_123045.csv

============================================================
[1/3] Processing profile
============================================================
🔗 URL: https://linkedin.com/in/john-doe/

📋 Step 1: Extracting profile data from LinkedIn...
✓ Name: John Doe
✓ Companies found: 2

🔍 Step 2: Searching for company domains on Google...

[1/2] Searching for: Example Corp
  ✓ Found domain for 'Example Corp': example.com

[2/2] Searching for: Previous Company
  ✓ Found domain for 'Previous Company': previous.com

✓ Domains found: 2
  • Example Corp → example.com
  • Previous Company → previous.com

📧 Step 3: Generating email addresses...
✓ Generated 2 email addresses:
  • john.doe@example.com
  • john.doe@previous.com

💾 Saved: John Doe

============================================================
✅ ENRICHMENT COMPLETE
============================================================
✓ Successfully enriched: 3
✗ Failed: 0
📁 Output saved to: data/csv/profiles_enriched_20260104_123045.csv
```

### 6. Check Your Results

Open the output CSV file in `data/csv/`. You'll see:

```csv
Profile URL,First Name,Last Name,Full Name,Companies,Domains,Generated Emails,Status,Error Message
https://linkedin.com/in/john-doe/,John,Doe,John Doe,Example Corp; Previous Company,example.com; previous.com,john.doe@example.com; john.doe@previous.com,Success,
```

## Example Scenarios

### Scenario 1: Person with Multi-Part Name

**LinkedIn Profile**: "Youssef El Mansouri"  
**Companies**: Alcatel Lucent Enterprise, Orange France  
**Generated Emails**:
- `youssef.el-mansouri@al-enterprise.com`
- `youssef.el-mansouri@orange.fr`

### Scenario 2: Person with Accent in Name

**LinkedIn Profile**: "François Müller"  
**Companies**: Deutsche Bank, SAP  
**Generated Emails**:
- `francois.muller@deutschebank.com`
- `francois.muller@sap.com`

### Scenario 3: Person with No Companies

**LinkedIn Profile**: "Recent Graduate"  
**Status**: "No Companies"  
**Generated Emails**: None  
**Error Message**: "No companies found in experience section"

## Tips

✅ **Start with a small test**: Process 2-3 profiles first to verify everything works  
✅ **Check your CSV format**: Make sure the column name is correct  
✅ **Be patient**: The script adds delays to avoid detection  
✅ **Review results**: Manually verify a few emails for accuracy  

⚠️ **Don't rush**: Default delays are recommended  
⚠️ **Monitor progress**: Watch the console for errors  
⚠️ **Save your work**: Results are saved incrementally  

## Common Issues

**"Column 'Profile URL' not found in CSV"**
- Check your CSV column name
- Provide the exact column name when prompted

**"No companies found in experience section"**
- Profile may have no work experience
- Experience section may be set to private
- Check manually on LinkedIn

**"Could not find valid domain"**
- Company too small/local for Google search
- Google returned only social media links
- May need manual domain lookup

## Next Steps

After enrichment:
1. Review the output CSV
2. Verify a sample of generated emails
3. Use emails for your outreach campaigns
4. Keep track of valid vs. bounced emails to improve accuracy

## Need Help?

See `PROFILE_ENRICHER_README.md` for detailed documentation.

# Profile Enricher - Feature Documentation

## Overview

The **Profile Enricher** feature extracts LinkedIn profile information and generates professional email addresses based on company domains discovered via Google search.

## How It Works

### Workflow

1. **Read CSV File**: Load LinkedIn profile URLs from a CSV file
2. **For Each Profile**:
   - Visit the LinkedIn profile
   - Extract first name and last name
   - Scrape the experience section to get all companies
   - For each company, search Google to find the domain
   - Generate professional email addresses using pattern: `firstname.lastname@domain.com`
3. **Save Results**: Export enriched data to timestamped CSV file

### Email Format

- Pattern: `firstname.lastname@domain.com`
- Multi-part names use hyphens: `youssef.el-mansouri@al-enterprise.com`
- Handles accents and special characters: `françois` → `francois`
- Removes apostrophes: `o'brien` → `obrien`

## Usage

### CLI Usage

1. Run the CLI:
   ```bash
   python cli.py
   ```

2. Select option `7. Enrich LinkedIn profiles from CSV (Extract emails)`

3. Provide inputs:
   - **CSV file path**: Path to your input CSV file
   - **Column name**: Name of column containing LinkedIn URLs (default: `Profile URL`)
   - **Max profiles**: Maximum number of profiles to process (press Enter for all)

### Input CSV Format

Your CSV file must contain a column with LinkedIn profile URLs:

```csv
Profile URL,Name
https://www.linkedin.com/in/youssef-el-mansouri/,Youssef El Mansouri
https://www.linkedin.com/in/jane-doe/,Jane Doe
```

**Supported column names**: Any column name is supported - you'll specify it when running the script. Common examples:
- `Profile URL`
- `LinkedIn`
- `URL`
- `LinkedIn Profile`

### Output CSV Format

The enriched output CSV contains:

| Column | Description |
|--------|-------------|
| `Profile URL` | Original LinkedIn profile URL |
| `First Name` | Person's first name |
| `Last Name` | Person's last name |
| `Full Name` | Complete name |
| `Companies` | Semicolon-separated list of companies |
| `Domains` | Semicolon-separated list of discovered domains |
| `Generated Emails` | Semicolon-separated list of generated email addresses |
| `Status` | Processing status (Success, No Companies, No Domains, Error) |
| `Error Message` | Error details if processing failed |

**Example Output**:
```csv
Profile URL,First Name,Last Name,Full Name,Companies,Domains,Generated Emails,Status,Error Message
https://linkedin.com/in/youssef-el-mansouri/,Youssef,El Mansouri,Youssef El Mansouri,Alcatel Lucent Enterprise; Orange France,al-enterprise.com; orange.fr,youssef.el-mansouri@al-enterprise.com; youssef.el-mansouri@orange.fr,Success,
```

## Architecture

### Module Structure

```
scraper/profile_enricher/
├── __init__.py              # Module exports
├── csv_processor.py         # CSV reading/writing
├── profile_scraper.py       # LinkedIn profile extraction
├── domain_finder.py         # Google domain search
├── email_generator.py       # Email formatting logic
└── enricher.py             # Main orchestration
```

### Service Layer

- **Service**: `ProfileEnricherService`
- **Method**: `enrich_profiles_from_csv(driver, csv_file_path, url_column_name, max_profiles)`
- **Location**: `core/services/profile_enricher_service.py`

## Features

### ✅ Incremental Saving
- Each profile is saved immediately after processing
- Progress is preserved even if script is interrupted
- Safe to stop and resume

### ✅ Error Handling
- Gracefully handles missing profiles
- Continues processing even if individual profiles fail
- Logs detailed error messages in output CSV

### ✅ Domain Caching
- Google search results are cached during a session
- Reduces redundant searches for companies that appear multiple times
- Improves performance

### ✅ Rate Limiting
- Delays between profile visits (5 seconds)
- Delays between Google searches (3 seconds)
- Prevents triggering anti-bot protections

### ✅ Progress Tracking
- Clear console output showing current progress
- Step-by-step logging for each profile
- Final summary with success/failure counts

## Example Usage

### Example 1: Basic Usage

**Input CSV** (`profiles.csv`):
```csv
Profile URL
https://www.linkedin.com/in/florence-joubrel/
```

**Command**:
```bash
python cli.py
# Select: 7
# CSV file: data/csv/profiles.csv
# Column: Profile URL
# Max profiles: (press Enter for all)
```

**Output** (`profiles_enriched_20260104_001530.csv`):
```csv
Profile URL,First Name,Last Name,Full Name,Companies,Domains,Generated Emails,Status,Error Message
https://www.linkedin.com/in/florence-joubrel/,Florence,Joubrel,Florence Joubrel,Asteria; Agence Laurence Nicolas; TOP BAGAGE INTERNATIONAL; STAFF DÉCOR,agence-laurence-nicolas.fr; topbagage.com; staffdecor.com,florence.joubrel@agence-laurence-nicolas.fr; florence.joubrel@topbagage.com; florence.joubrel@staffdecor.com,Success,
```

### Example 2: Multi-Part Names

**Input**: Profile with name "Jean-Pierre De La Cruz"

**Generated Email**: `jean-pierre.de-la-cruz@company.com`

### Example 3: Names with Accents

**Input**: Profile with name "François Müller"

**Generated Email**: `francois.muller@company.com`

## Limitations & Considerations

### ⚠️ Email Format Assumption
The implementation assumes all companies use the format `firstname.lastname@domain.com`. Some companies may use different patterns:
- `firstlast@domain.com`
- `f.last@domain.com`
- `firstname@domain.com`

If you need alternative formats, the email generation logic can be extended.

### ⚠️ Google Rate Limiting
- Google may show CAPTCHA challenges after many searches
- Consider adding longer delays if you encounter issues
- Domain caching helps reduce search volume

### ⚠️ LinkedIn Detection
- The script follows existing anti-detection patterns
- Uses randomized delays between profiles
- Respects LinkedIn's structure changes

### ⚠️ Company Name Variations
- Company names on LinkedIn may differ from official names
- Example: "Alcatel-Lucent Enterprise" vs "ALE"
- May require manual verification for accuracy

## Tips for Best Results

1. **Start Small**: Test with 2-3 profiles first
2. **Verify Output**: Manually check a few generated emails
3. **Monitor Progress**: Watch the console for any errors
4. **Use Delays**: Don't rush - the default delays are recommended
5. **Clean Input**: Ensure LinkedIn URLs are valid and accessible

## Troubleshooting

### Issue: "Column not found in CSV"
**Solution**: Check the exact column name in your CSV and provide it when prompted

### Issue: "No companies found"
**Solution**: Profile may not have an experience section or it's set to private

### Issue: "Could not find domain"
**Solution**: 
- Company may be too small/local
- Google search returned social media links only
- Try manual verification

### Issue: Script stops unexpectedly
**Solution**: Check `data/logs/` for error details. Output CSV will contain progress up to the interruption point.

## File Locations

- **Input CSV**: Anywhere on your system
- **Output CSV**: `data/csv/[filename]_enriched_[timestamp].csv`
- **Logs**: `data/logs/` (if logging is configured)

## Development

### Running Tests

Currently no automated tests. Manual testing is recommended:

1. Create a test CSV with 2-3 known profiles
2. Run the enricher
3. Verify output manually

### Extending the Feature

**To add alternative email formats**:
1. Edit `scraper/profile_enricher/email_generator.py`
2. Add new generation functions
3. Update `generate_emails_for_profile()` to return multiple formats

**To improve domain detection**:
1. Edit `scraper/profile_enricher/domain_finder.py`
2. Enhance Google search query or parsing logic
3. Add fallback domain sources (company website databases)

## Support

For issues or feature requests, refer to the main project documentation or contact the development team.

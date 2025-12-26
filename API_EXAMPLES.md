# LinkedIn Scraper API - Usage Examples

This document provides detailed examples of how to use the LinkedIn Scraper API.

## Table of Contents
- [Authentication](#authentication)
- [Scraping Operations](#scraping-operations)
- [Connection Operations](#connection-operations)
- [Messaging Operations](#messaging-operations)
- [Python Client Example](#python-client-example)

## Authentication

All API requests require an API key in the `X-API-Key` header:

```bash
X-API-Key: dev-api-key-change-in-production
```

⚠️ **Important**: Change the default API key before deploying to production!

## Scraping Operations

### 1. Scrape LinkedIn Group Members

Scrape members from a LinkedIn group with optional limits.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/scrape/group" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "group_url": "https://www.linkedin.com/groups/12345/",
    "max_members": 100,
    "scraping_mode": "smart"
  }'
```

**Response:**
```json
{
  "job_id": "job_abc123xyz",
  "status": "pending",
  "message": "Group scraping job created successfully",
  "created_at": "2025-12-26T19:42:00Z"
}
```

### 2. Search and Scrape Profiles

Search LinkedIn for profiles matching keywords.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/scrape/search" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": "python developer",
    "max_profiles": 50,
    "start_page": 1
  }'
```

**Response:**
```json
{
  "job_id": "job_def456uvw",
  "status": "pending",
  "message": "Search scraping job created successfully",
  "created_at": "2025-12-26T19:43:00Z"
}
```

### 3. Google-Based Profile Scraping

Use Google search to find LinkedIn profiles.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/scrape/google" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": "developer engineer programmer",
    "oblig_keywords": "python senior",
    "max_profiles": 100,
    "max_profiles_per_keyword": 20
  }'
```

**Response:**
```json
{
  "job_id": "job_ghi789rst",
  "status": "pending",
  "message": "Google scraping job created successfully",
  "created_at": "2025-12-26T19:44:00Z"
}
```

### 4. Check Job Status

Monitor the progress of any scraping job.

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/scrape/status/job_abc123xyz" \
  -H "X-API-Key: dev-api-key-change-in-production"
```

**Response (Running):**
```json
{
  "job_id": "job_abc123xyz",
  "status": "running",
  "progress": 45,
  "message": "Job is running",
  "result": null,
  "error": null
}
```

**Response (Completed):**
```json
{
  "job_id": "job_abc123xyz",
  "status": "completed",
  "progress": 100,
  "message": "Job is completed",
  "result": {
    "success": true,
    "total_scraped": 100,
    "scraping_mode": "smart",
    "message": "Successfully scraped 100 members"
  },
  "error": null
}
```

## Connection Operations

### 1. Send Single Connection Request

Send a connection request to a specific LinkedIn profile.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/connections/send" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_url": "https://www.linkedin.com/in/johndoe/",
    "note_message": "Hi John, I'\''d love to connect and learn about your work!"
  }'
```

**Response:**
```json
{
  "job_id": "job_conn123",
  "status": "pending",
  "message": "Connection request job created successfully",
  "created_at": "2025-12-26T19:45:00Z"
}
```

### 2. Send Mass Connection Requests

Send connection requests to multiple profiles from a CSV file.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/connections/mass-send" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "csv_file_path": "./data/profiles.csv",
    "note_message": "Hi, I'\''d like to connect!",
    "use_note": true
  }'
```

**Response:**
```json
{
  "job_id": "job_mass456",
  "status": "pending",
  "message": "Mass connection job created successfully",
  "created_at": "2025-12-26T19:46:00Z"
}
```

### 3. Check Connection Job Status

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/connections/status/job_conn123" \
  -H "X-API-Key: dev-api-key-change-in-production"
```

## Messaging Operations

### 1. Send Messages to Group Members

Send messages to LinkedIn group members.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/messages/group" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "group_data_file": "./data/group_members.csv"
  }'
```

**Response:**
```json
{
  "job_id": "job_msg789",
  "status": "pending",
  "message": "Group messaging job created successfully",
  "created_at": "2025-12-26T19:47:00Z"
}
```

### 2. Check Messaging Job Status

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/messages/status/job_msg789" \
  -H "X-API-Key: dev-api-key-change-in-production"
```

## Python Client Example

Here's a complete Python client for the API:

```python
import requests
import time
from typing import Dict, Any, Optional


class LinkedInScraperAPI:
    """Python client for LinkedIn Scraper API"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = "dev-api-key-change-in-production"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def scrape_group(self, group_url: str, max_members: Optional[int] = None, 
                     scraping_mode: str = "smart") -> Dict[str, Any]:
        """Scrape LinkedIn group members"""
        endpoint = f"{self.base_url}/api/v1/scrape/group"
        payload = {
            "group_url": group_url,
            "max_members": max_members,
            "scraping_mode": scraping_mode
        }
        response = requests.post(endpoint, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def search_profiles(self, keywords: str, max_profiles: int, start_page: int = 1) -> Dict[str, Any]:
        """Search and scrape LinkedIn profiles"""
        endpoint = f"{self.base_url}/api/v1/scrape/search"
        payload = {
            "keywords": keywords,
            "max_profiles": max_profiles,
            "start_page": start_page
        }
        response = requests.post(endpoint, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_job_status(self, job_id: str, endpoint_type: str = "scrape") -> Dict[str, Any]:
        """Get job status"""
        endpoint = f"{self.base_url}/api/v1/{endpoint_type}/status/{job_id}"
        response = requests.get(endpoint, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def wait_for_job(self, job_id: str, endpoint_type: str = "scrape", 
                     max_wait: int = 3600, check_interval: int = 5) -> Dict[str, Any]:
        """Wait for job to complete and return result"""
        elapsed = 0
        while elapsed < max_wait:
            status = self.get_job_status(job_id, endpoint_type)
            
            if status["status"] == "completed":
                return status["result"]
            elif status["status"] == "failed":
                raise Exception(f"Job failed: {status.get('error')}")
            
            time.sleep(check_interval)
            elapsed += check_interval
        
        raise TimeoutError(f"Job did not complete within {max_wait} seconds")
    
    def send_connection(self, profile_url: str, note_message: Optional[str] = None) -> Dict[str, Any]:
        """Send a connection request"""
        endpoint = f"{self.base_url}/api/v1/connections/send"
        payload = {
            "profile_url": profile_url,
            "note_message": note_message
        }
        response = requests.post(endpoint, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        endpoint = f"{self.base_url}/health"
        response = requests.get(endpoint)
        response.raise_for_status()
        return response.json()


# Usage Example
if __name__ == "__main__":
    # Initialize client
    client = LinkedInScraperAPI(
        base_url="http://localhost:8000",
        api_key="dev-api-key-change-in-production"
    )
    
    # Check API health
    health = client.health_check()
    print(f"API Status: {health['status']}")
    
    # Scrape group members
    job = client.scrape_group(
        group_url="https://www.linkedin.com/groups/12345/",
        max_members=50,
        scraping_mode="smart"
    )
    print(f"Job created: {job['job_id']}")
    
    # Wait for completion
    try:
        result = client.wait_for_job(job['job_id'], endpoint_type="scrape")
        print(f"Scraping completed: {result}")
    except Exception as e:
        print(f"Error: {e}")
```

## Error Handling

### Common Error Responses

**401 Unauthorized - Missing API Key:**
```json
{
  "detail": "API key is missing"
}
```

**403 Forbidden - Invalid API Key:**
```json
{
  "detail": "Invalid API key"
}
```

**404 Not Found - Job Not Found:**
```json
{
  "detail": "Job not found"
}
```

**500 Internal Server Error:**
```json
{
  "error": "InternalServerError",
  "message": "An unexpected error occurred",
  "detail": "..."
}
```

## Rate Limiting

The API has built-in rate limiting:
- **Per minute**: 60 requests
- **Per hour**: 1000 requests

Exceeding these limits will result in a `429 Too Many Requests` response.

## Best Practices

1. **Poll job status** every 5-10 seconds (not more frequently)
2. **Handle errors gracefully** with proper try-catch blocks
3. **Respect LinkedIn's rate limits** to avoid account restrictions
4. **Store results** from completed jobs before they expire
5. **Use background jobs** for all long-running operations

## Support

For issues or questions, check the main README.md or review the API documentation at `/docs`.

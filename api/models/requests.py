"""
API Request Models - Pydantic schemas for request validation
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class GroupScrapeRequest(BaseModel):
    """Request model for group scraping"""
    group_url: str = Field(..., description="LinkedIn group URL")
    max_members: Optional[int] = Field(None, description="Maximum members to scrape (None for unlimited)")
    scraping_mode: str = Field("medium", description="Scraping mode: 'light', 'medium', or 'robust'")

    @field_validator("scraping_mode")
    @classmethod
    def validate_scraping_mode(cls, v):
        valid = {"light", "medium", "robust"}
        if v not in valid:
            raise ValueError(f"scraping_mode must be one of {valid}, got '{v}'")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "group_url": "https://www.linkedin.com/groups/12345/",
                "max_members": 100,
                "scraping_mode": "medium"
            }
        }


class SearchScrapeRequest(BaseModel):
    """Request model for search-based scraping"""
    keywords: str = Field(..., description="Search keywords")
    max_profiles: int = Field(..., description="Maximum profiles to scrape", gt=0)
    start_page: int = Field(1, description="Starting page number", gt=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "keywords": "technical recruiter",
                "max_profiles": 50,
                "start_page": 1
            }
        }


class GoogleScrapeRequest(BaseModel):
    """Request model for Google-based LinkedIn scraping"""
    keywords: str = Field(..., description="Search keywords (space-separated)")
    oblig_keywords: str = Field("", description="Obligatory keywords (space-separated)")
    max_profiles: int = Field(50, description="Maximum total profiles", gt=0)
    max_profiles_per_keyword: int = Field(20, description="Maximum profiles per keyword", gt=0)
    max_pages: int = Field(10, description="Max Google pages per keyword", gt=0)
    verbose: bool = Field(True, description="Verbose logging")

    class Config:
        json_schema_extra = {
            "example": {
                "keywords": "developer engineer programmer",
                "oblig_keywords": "python senior",
                "max_profiles": 100,
                "max_profiles_per_keyword": 20,
                "max_pages": 10,
                "verbose": True,
            }
        }


class EnrichFromDBRequest(BaseModel):
    """Request model for enriching profiles already in the database"""
    max_profiles: Optional[int] = Field(None, description="Max profiles to enrich (None = all)")
    profile_indices: Optional[list] = Field(None, description="Specific 1-based indices")
    range_start: Optional[int] = Field(None, description="1-based start of range")
    range_end: Optional[int] = Field(None, description="1-based end of range (inclusive)")

    class Config:
        json_schema_extra = {
            "example": {
                "max_profiles": 50
            }
        }


class ConnectionRequest(BaseModel):
    """Request model for sending connection"""
    profile_url: str = Field(..., description="LinkedIn profile URL")
    note_message: Optional[str] = Field(None, description="Personal note (max 300 characters)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "profile_url": "https://www.linkedin.com/in/johndoe/",
                "note_message": "Hi, I'd like to connect with you!"
            }
        }


class MassConnectionRequest(BaseModel):
    """Request model for mass connection sending"""
    csv_file_path: str = Field(..., description="Path to CSV file with profile URLs")
    note_message: Optional[str] = Field(None, description="Personal note (max 300 characters)")
    use_note: bool = Field(False, description="Whether to include the note")
    
    class Config:
        json_schema_extra = {
            "example": {
                "csv_file_path": "./data/profiles.csv",
                "note_message": "Hi, I'd like to connect!",
                "use_note": True
            }
        }


class MessageRequest(BaseModel):
    """Request model for group messaging"""
    # Note: The current implementation uses data from previous scraping
    # This is a placeholder for future enhancements
    group_data_file: Optional[str] = Field(None, description="Path to group data CSV")
    
    class Config:
        json_schema_extra = {
            "example": {
                "group_data_file": "./data/group_members.csv"
            }
        }

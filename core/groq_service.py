"""
Groq AI Service - Wrapper for Groq API with free-tier model support.
Handles rate limits (429 errors) with 60-second delays and model fallback.
"""
import os
import time
import logging
from typing import Dict, List, Optional

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

logger = logging.getLogger(__name__)


# Model options (free tier - no credit card required)
GROQ_MODELS = {
    # Primary: Best quality for LaTeX generation
    "llama-3.3-70b-versatile": {
        "rpm": 30,
        "tpm": 12000,
        "rpd": 1000,
        "description": "Best quality LaTeX/code (recommended)",
    },
    # Alternative 1: Reasoning-capable, 120B parameters
    "openai/gpt-oss-120b": {
        "rpm": 30,
        "tpm": 8000,
        "rpd": 1000,
        "description": "120B parameters, reasoning-capable",
    },
    # Alternative 2: Fast, efficient
    "meta-llama/llama-4-scout-17b-16e-instruct": {
        "rpm": 30,
        "tpm": 30000,
        "rpd": 1000,
        "description": "Fast, 17B parameters",
    },
    # Alternative 3: Good reasoning
    "qwen/qwen3-32b": {
        "rpm": 60,
        "tpm": 6000,
        "rpd": 1000,
        "description": "Good reasoning, 32B parameters",
    },
}


class GroqService:
    """Service for Groq API with rate limit handling and model fallback."""

    def __init__(self, api_key: str = None, model: str = "llama-3.3-70b-versatile"):
        """
        Initialize Groq service.
        Args:
            api_key: Groq API key (or set GROQ_API_KEY env var)
            model: Model to use (see GROQ_MODELS for options)
        """
        if not GROQ_AVAILABLE:
            raise ImportError(
                "groq package not installed. Run: pip install groq"
            )

        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "Groq API key required. Set GROQ_API_KEY or pass api_key."
            )

        self.client = Groq(api_key=self.api_key)
        self.model = model
        self.logger = logger

        # Fallback model chain
        self.fallback_models = [
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "qwen/qwen3-32b",
        ]
        # Remove duplicates while preserving order
        seen = set()
        self.fallback_models = [
            m for m in self.fallback_models if not (m in seen or seen.add(m))
        ]

    def generate_latex(self, prompt: str, max_tokens: int = 4000,
                        temperature: float = 0.7, max_retries: int = 3) -> str:
        """
        Generate LaTeX code using Groq with rate limit handling.
        Args:
            prompt: The prompt for LaTeX generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-2)
            max_retries: Max retries per model before switching
        Returns:
            Generated LaTeX code as string
        """
        models_to_try = [self.model] + [
            m for m in self.fallback_models if m != self.model
        ]

        for model_idx, model_name in enumerate(models_to_try):
            if model_idx > 0:
                self.logger.warning(
                    "Falling back to model: %s", model_name
                )

            for attempt in range(max_retries):
                try:
                    self.logger.debug(
                        "Generating with %s (attempt %d/%d)",
                        model_name, attempt + 1, max_retries
                    )

                    response = self.client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model=model_name,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

                    result = response.choices[0].message.content
                    if result:
                        self.logger.success(
                            "Generated %d chars with %s",
                            len(result), model_name
                        )
                        return result
                    else:
                        raise Exception("Empty response from API")

                except Exception as e:
                    error_str = str(e).lower()

                    # Rate limit (429 error)
                    if "429" in error_str or "rate" in error_str:
                        if attempt < max_retries - 1:
                            self.logger.warning(
                                "Rate limit hit on %s, waiting 60s (attempt %d/%d)",
                                model_name, attempt + 1, max_retries
                            )
                            time.sleep(60)
                            continue
                        else:
                            self.logger.error(
                                "Rate limit exceeded for %s after %d attempts",
                                model_name, max_retries
                            )
                            break  # Try next model

                    # Other errors
                    else:
                        if attempt < max_retries - 1:
                            self.logger.warning(
                                "Error with %s: %s (retrying in 5s)",
                                model_name, e
                            )
                            time.sleep(5)
                            continue
                        else:
                            self.logger.error(
                                "Failed with %s after %d attempts: %s",
                                model_name, max_retries, e
                            )
                            break  # Try next model

        raise Exception("All models failed to generate LaTeX")

    def generate_cv_section(self, profile_data: Dict, section: str,
                           base_content: str = "") -> str:
        """
        Generate a specific CV section using AI.
        Args:
            profile_data: Profile information dict
            section: Section name ("experiences", "education", "skills")
            base_content: Optional base content to modify
        Returns:
            LaTeX code for the section
        """
        if section == "experiences":
            prompt = f"""
You are a LaTeX CV expert. Given this profile's experiences:
{profile_data.get('experiences', [])}

And current company: {profile_data.get('current_company', '')}

Generate a LaTeX \\begin{{itemize}}...\\end{{itemize}} section for ATS-optimized CV that:
1. Uses action verbs (Developed, Led, Optimized)
2. Quantifies achievements where possible (%, numbers)
3. Emphasizes experiences relevant to {profile_data.get('current_company', 'target company')}
4. Uses ATS-friendly formatting (no special characters)
5. Limits to 3-5 bullets per job
6. Matches skills to the target company's industry

Return ONLY the LaTeX code, no explanation.
"""
        elif section == "education":
            prompt = f"""
Given this education data:
{profile_data.get('education', [])}

Generate a LaTeX \\begin{{itemize}}...\\end{{itemize}} section:
- List each education entry with school, degree, field, dates
- Use proper LaTeX formatting
- Keep ATS-friendly

Return ONLY the LaTeX code.
"""
        elif section == "skills":
            prompt = f"""
Given this profile:
- Name: {profile_data.get('full_name', '')}
- Current company: {profile_data.get('current_company', '')}
- Experiences: {profile_data.get('experiences', [])}

Generate a LaTeX \\begin{{itemize}}...\\end{{itemize}} section listing skills that:
1. Prioritize skills that match {profile_data.get('current_company', 'target company')} industry
2. Include skills from the profile's experiences
3. Use ATS-relevant keywords
4. Limit to 8-12 most relevant skills

Return ONLY the LaTeX code.
"""
        else:
            raise ValueError(f"Unknown section: {section}")

        return self.generate_latex(prompt)

    def customize_cover_letter(self, profile_data: Dict, company: str,
                               base_letter: str = "") -> str:
        """
        Generate a customized cover letter for a profile.
        Args:
            profile_data: Profile information
            company: Target company
            base_letter: Optional base letter to modify
        Returns:
            Customized cover letter text
        """
        prompt = f"""
You are a professional cover letter writer. Given:
- Profile: {profile_data.get('full_name', '')}
- Current role: {profile_data.get('current_job_title', '')}
- Current company: {profile_data.get('current_company', '')}
- About: {profile_data.get('about_text', '')[:500]}

Generate a professional cover letter for {company} that:
1. Highlights relevant experiences from the profile
2. Explains why they're a good fit for {company}
3. Uses professional tone
4. Is 200-300 words

Return ONLY the cover letter text, no explanation.
"""
        return self.generate_latex(prompt, max_tokens=1000)

    def customize_email(self, profile_data: Dict, base_email: str) -> str:
        """
        Customize email body for a specific profile.
        Args:
            profile_data: Profile information
            base_email: Base email template
        Returns:
            Customized email text
        """
        prompt = f"""
Given this email template:
{base_email}

And this profile:
- Name: {profile_data.get('full_name', '')}
- Company: {profile_data.get('current_company', '')}
- Title: {profile_data.get('current_job_title', '')}

Rewrite the email to:
1. Be more relevant to {profile_data.get('full_name', 'the person')}
2. Reference their background/company naturally
3. Keep the same general structure/purpose
4. Be professional and personalized

Return ONLY the customized email text.
"""
        return self.generate_latex(prompt, max_tokens=500)

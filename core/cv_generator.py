"""
CV Generator - AI-powered LaTeX CV generation using Groq API.
Generates customized CV sections based on profile data.
"""
import os
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Check if Groq is available
try:
    from core.groq_service import GroqService
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    GroqService = None


def generate_experiences_section(profile_data: Dict, groq: GroqService) -> str:
    """
    Generate LaTeX experiences section using AI.
    Args:
        profile_data: Profile dictionary from database
        groq: GroqService instance
    Returns:
        LaTeX code for experiences section
    """
    experiences = profile_data.get('experiences', [])
    if not experiences:
        return ""

    # Parse JSON if needed
    if isinstance(experiences, str):
        try:
            experiences = json.loads(experiences)
        except Exception:
            return ""

    if not isinstance(experiences, list) or not experiences:
        return ""

    # Build prompt
    prompt = f"""
You are a LaTeX CV expert. Given this profile's experiences:
{json.dumps(experiences, indent=2)}

And current company: {profile_data.get('current_company', '')}

Generate a LaTeX \\begin{{itemize}}...\\end{{itemize}} section for an ATS-optimized CV that:
1. Uses action verbs (Developed, Led, Optimized, etc.)
2. Quantifies achievements where possible (%, numbers, scale)
3. Emphasizes experiences relevant to {profile_data.get('current_company', 'the target company')}
4. Uses ATS-friendly formatting (no special characters, proper escapes)
5. Limits to 3-5 bullets per job
6. Matches skills/keywords to the target company's industry

Return ONLY the LaTeX code, no explanation, no ``` markers.
"""
    
    try:
        result = groq.generate_latex(prompt)
        # Validate it looks like LaTeX
        if "\\begin{itemize}" in result and "\\end{itemize}" in result:
            return result
        else:
            logger.warning("Generated experiences doesn't contain itemize environment")
            return _fallback_experiences(experiences)
    except Exception as e:
        logger.error("Error generating experiences: %s", e)
        return _fallback_experiences(experiences)


def generate_education_section(education_data: List, groq: GroqService = None) -> str:
    """
    Generate LaTeX education section from profile data.
    Args:
        education_data: List of education dictionaries
        groq: Optional GroqService (not used for education - deterministic)
    Returns:
        LaTeX code for education section
    """
    if not education_data:
        return ""

    if isinstance(education_data, str):
        try:
            education_data = json.loads(education_data)
        except Exception:
            return ""

    if not isinstance(education_data, list) or not education_data:
        return ""

    lines = ["\\begin{itemize}"]
    for edu in education_data:
        school = edu.get('school', '')
        degree = edu.get('degree', '')
        field = edu.get('field', '')
        dates = edu.get('dates', '')

        line = f"  \\item \\textbf{{{school}}}"
        if degree:
            line += f", {degree}"
        if field:
            line += f" -- {field}"
        if dates:
            line += f" ({dates})"
        lines.append(line)

    lines.append("\\end{itemize}")
    return "\n".join(lines)


def generate_skills_section(profile_data: Dict, groq: GroqService) -> str:
    """
    Generate prioritized LaTeX skills section using AI.
    Args:
        profile_data: Profile dictionary
        groq: GroqService instance
    Returns:
        LaTeX code for skills section
    """
    prompt = f"""
Given this profile data:
- Name: {profile_data.get('full_name', '')}
- Current company: {profile_data.get('current_company', '')}
- Current title: {profile_data.get('current_job_title', '')}
- About: {profile_data.get('about_text', '')[:300]}

And target company: {profile_data.get('current_company', '')}

Generate a LaTeX \\begin{{itemize}}...\\end{{itemize}} section listing 8-12 technical skills that:
1. Prioritize skills that match {profile_data.get('current_company', 'the target')} industry/tech stack
2. Include skills from the profile's experiences
3. Use ATS-relevant keywords
4. Are formatted as: \\item Skill Name
5. Group related skills if possible (e.g., "Programming: Python, JavaScript")

Return ONLY the LaTeX code, no explanation.
"""
    
    try:
        result = groq.generate_latex(prompt)
        if "\\begin{itemize}" in result and "\\end{itemize}" in result:
            return result
        else:
            return _fallback_skills()
    except Exception as e:
        logger.error("Error generating skills: %s", e)
        return _fallback_skills()


def generate_cv_for_profile(profile_url: str, groq: GroqService,
                              base_cv_path: str = "templates/base_cv.tex",
                              output_dir: str = "data/documents/generated_cvs") -> str:
    """
    Generate a customized LaTeX CV for a profile.
    Args:
        profile_url: LinkedIn profile URL
        groq: GroqService instance
        base_cv_path: Path to base CV template
        output_dir: Directory for output files
    Returns:
        Path to generated .tex file
    """
    from core.database import get_connection

    # 1. Query profile data from database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM enriched_profiles WHERE profile_url = ?",
        (profile_url,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise Exception(f"Profile not found: {profile_url}")

    profile = dict(row)
    profile_id = profile['id']

    logger.info("Generating CV for %s (ID: %d)", profile.get('full_name', ''), profile_id)

    # 2. Read base CV template
    if not os.path.exists(base_cv_path):
        raise FileNotFoundError(f"Base CV not found: {base_cv_path}")

    with open(base_cv_path, 'r', encoding='utf-8') as f:
        base_cv = f.read()

    # 3. Generate customized sections using Groq
    logger.info("Generating experiences section...")
    experiences_latex = generate_experiences_section(profile, groq)

    logger.info("Generating education section...")
    education = []
    try:
        if profile.get('education'):
            if isinstance(profile['education'], str):
                education = json.loads(profile['education'])
            else:
                education = profile['education']
    except Exception:
        pass
    education_latex = generate_education_section(education, groq)

    logger.info("Generating skills section...")
    skills_latex = generate_skills_section(profile, groq)

    # 4. Replace placeholders in base CV
    cv_content = base_cv

    # Replace experiences placeholder
    if "% AI_EXPERIENCES_SECTION" in cv_content:
        cv_content = cv_content.replace(
            "% AI_EXPERIENCES_SECTION",
            experiences_latex
        )
    else:
        # Try to find experiences section
        cv_content = cv_content.replace(
            "\\section*{Experience}",
            "\\section*{Experience}\n" + experiences_latex
        )

    # Replace education placeholder
    if "% AI_EDUCATION_SECTION" in cv_content:
        cv_content = cv_content.replace(
            "% AI_EDUCATION_SECTION",
            education_latex
        )

    # Replace skills placeholder
    if "% AI_SKILLS_SECTION" in cv_content:
        cv_content = cv_content.replace(
            "% AI_SKILLS_SECTION",
            skills_latex
        )

    # 5. Save .tex file
    os.makedirs(output_dir, exist_ok=True)
    tex_path = os.path.join(output_dir, f"profile_{profile_id}.tex")

    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(cv_content)

    logger.success("Generated CV: %s", tex_path)

    # 6. Update database with CV path
    try:
        from core.database import update_profile_cv
        update_profile_cv(profile_url, tex_path)
    except Exception as e:
        logger.warning("Could not update database: %s", e)

    return tex_path


def compile_latex_to_pdf(tex_path: str) -> Optional[str]:
    """
    Compile LaTeX to PDF using pdflatex.
    Args:
        tex_path: Path to .tex file
    Returns:
        Path to generated PDF, or None if compilation fails
    """
    import subprocess

    if not os.path.exists(tex_path):
        logger.error("TeX file not found: %s", tex_path)
        return None

    output_dir = os.path.dirname(tex_path)

    try:
        # Try pdflatex
        result = subprocess.run(
            ["pdflatex", "-output-directory", output_dir, tex_path],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            pdf_path = tex_path.replace(".tex", ".pdf")
            if os.path.exists(pdf_path):
                logger.success("Compiled PDF: %s", pdf_path)
                return pdf_path
            else:
                raise Exception("PDF not created after successful compilation")
        else:
            # Check for LaTeX errors
            log_file = tex_path.replace(".tex", ".log")
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()
                # Extract error lines
                error_lines = [l for l in log_content.split('\n') if 'error' in l.lower()][:5]
                logger.error("LaTeX errors: %s", error_lines)
            raise Exception(f"pdflatex failed with return code {result.returncode}")

    except FileNotFoundError:
        logger.warning("pdflatex not installed. Install MiKTeX (Windows) or TeX Live (Linux)")
        logger.info("You can manually compile: pdflatex %s", tex_path)
        return None
    except subprocess.TimeoutExpired:
        logger.error("pdflatex timeout (60s)")
        return None
    except Exception as e:
        logger.error("Compilation error: %s", e)
        return None


def _fallback_experiences(experiences: List) -> str:
    """Generate experiences section without AI (fallback)."""
    lines = ["\\begin{itemize}"]
    for exp in experiences[:5]:  # Limit to 5 most recent
        title = exp.get('title', '')
        company = exp.get('company', '')
        dates = exp.get('dates', '')
        description = exp.get('description', '')[:200]

        line = f"  \\item \\textbf{{{title}}} at {company}"
        if dates:
            line += f" ({dates})"
        if description:
            line += f"\\\\ {description}"
        lines.append(line)
    lines.append("\\end{itemize}")
    return "\n".join(lines)


def _fallback_skills() -> str:
    """Generate generic skills section (fallback)."""
    return """\\begin{itemize}
  \\item Programming: Python, JavaScript, SQL
  \\item Frameworks: React, Node.js, Django
  \\item Tools: Git, Docker, AWS
  \\item Soft Skills: Team Leadership, Project Management
\\end{itemize}"""

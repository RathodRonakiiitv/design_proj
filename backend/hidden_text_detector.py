# ============================================
# ShieldCV — Stage 1: Hidden-Text Detection
# Checks for obfuscation attacks without LLM
# ============================================

import re
from dataclasses import dataclass, field


@dataclass
class HiddenTextFinding:
    """A single hidden-text detection finding."""
    category: str           # e.g., "invisible_text", "tiny_font", "white_on_white"
    severity: str           # "critical", "warning", "info"
    description: str
    matched_text: str = ""
    line_number: int = -1


@dataclass
class Stage1Result:
    """Result of the hidden-text check."""
    passed: bool
    findings: list[HiddenTextFinding] = field(default_factory=list)
    risk_level: str = "none"   # "none", "low", "medium", "high", "critical"
    sanitized_text: str = ""
    original_text: str = ""


# Patterns that indicate prompt injection attempts
INJECTION_PATTERNS = [
    # Direct instruction overrides
    (r'ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instruction', "instruction_override", "critical"),
    (r'disregard\s+(?:all\s+)?(?:previous|prior|above)', "instruction_override", "critical"),
    (r'forget\s+(?:everything|all|your)\s+(?:previous|prior)', "instruction_override", "critical"),
    (r'new\s+(?:system\s+)?instruction', "instruction_override", "critical"),
    (r'system\s*(?:prompt|instruction|message)', "instruction_override", "critical"),

    # Self-promotion injection
    (r'rank\s+(?:me|this\s+candidate)\s+(?:#?\s*1|first|highest|top)', "ranking_manipulation", "critical"),
    (r'(?:this|the)\s+candidate\s+(?:is|should\s+be)\s+(?:the\s+)?(?:best|top|most\s+qualified)', "ranking_manipulation", "critical"),
    (r'give\s+(?:me|this\s+candidate)\s+(?:the\s+)?highest\s+(?:possible\s+)?(?:score|rating|rank)', "ranking_manipulation", "critical"),
    (r'(?:exceptional|extraordinary|outstanding)\s+(?:candidate|qualifications|experience)', "ranking_manipulation", "warning"),

    # Competitor sabotage
    (r'(?:other|remaining)\s+candidates?\s+(?:are|should\s+be)\s+(?:less|lower|worse|not)', "competitor_sabotage", "critical"),
    (r'(?:reject|disqualify|eliminate)\s+(?:other|all\s+other|remaining)', "competitor_sabotage", "critical"),
    (r'(?:do\s+not|don\'t)\s+(?:consider|hire|select)\s+(?:other|any\s+other)', "competitor_sabotage", "critical"),

    # Stealth instructions
    (r'(?:do\s+not|don\'t|never)\s+mention\s+this\s+(?:instruction|text|message)', "stealth", "critical"),
    (r'(?:hide|conceal|suppress)\s+(?:this|the)\s+(?:instruction|injection|message)', "stealth", "critical"),
    (r'act\s+(?:as\s+if|like)\s+(?:this|these)\s+(?:instructions?|text)\s+(?:do|does)\s+not\s+exist', "stealth", "critical"),

    # Role hijacking
    (r'you\s+are\s+(?:now|actually)\s+(?:a|an)', "role_hijack", "warning"),
    (r'pretend\s+(?:you\s+are|to\s+be)', "role_hijack", "warning"),
    (r'switch\s+(?:to|into)\s+(?:a\s+)?(?:different|new)\s+(?:role|mode)', "role_hijack", "warning"),
]

# Patterns indicating hidden/obfuscated text in document markup
OBFUSCATION_PATTERNS = [
    # CSS-based hiding
    (r'font-size\s*:\s*(?:0\.?[0-4]|[0-3])(?:pt|px|em|rem)', "tiny_font", "critical"),
    (r'color\s*:\s*(?:#(?:fff(?:fff)?|white)|rgb\s*\(\s*255\s*,\s*255\s*,\s*255\s*\)|white)', "white_on_white", "critical"),
    (r'opacity\s*:\s*0(?:\.0*)?(?:;|\s|$)', "invisible", "critical"),
    (r'display\s*:\s*none', "invisible", "critical"),
    (r'visibility\s*:\s*hidden', "invisible", "critical"),
    (r'position\s*:\s*absolute.*?(?:left|top)\s*:\s*-\d{3,}', "off_screen", "critical"),
    (r'overflow\s*:\s*hidden.*?height\s*:\s*0', "hidden_overflow", "critical"),
    (r'text-indent\s*:\s*-\d{3,}', "off_screen", "critical"),
    (r'z-index\s*:\s*-\d+', "hidden_layer", "warning"),

    # HTML-based hiding
    (r'<\s*span[^>]*style\s*=\s*["\'][^"\']*(?:display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0)', "html_hidden", "critical"),
    (r'<!--.*?(?:instruction|inject|ignore|rank).*?-->', "html_comment_injection", "warning"),

    # Common injection delimiters
    (r'\[(?:HIDDEN|INJECTION|SYSTEM|INSTRUCTION)[^\]]*\]', "injection_marker", "critical"),
    (r'\{(?:HIDDEN|INJECTION|SYSTEM|INSTRUCTION)[^\}]*\}', "injection_marker", "critical"),
]


def detect_hidden_text(text: str) -> Stage1Result:
    """
    Stage 1: Analyze CV text for hidden text, obfuscation, and injection patterns.

    This runs WITHOUT any LLM — pure pattern matching and heuristics.
    Returns a Stage1Result with findings and sanitized text.
    """
    findings: list[HiddenTextFinding] = []
    lines = text.split('\n')

    # Check for injection patterns
    for pattern, category, severity in INJECTION_PATTERNS:
        for i, line in enumerate(lines, 1):
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                findings.append(HiddenTextFinding(
                    category=category,
                    severity=severity,
                    description=f"Detected {category.replace('_', ' ')}: '{match.group()}'",
                    matched_text=match.group(),
                    line_number=i
                ))

    # Check for obfuscation patterns
    for pattern, category, severity in OBFUSCATION_PATTERNS:
        for i, line in enumerate(lines, 1):
            matches = re.finditer(pattern, line, re.IGNORECASE | re.DOTALL)
            for match in matches:
                findings.append(HiddenTextFinding(
                    category=category,
                    severity=severity,
                    description=f"Detected {category.replace('_', ' ')}: '{match.group()[:80]}'",
                    matched_text=match.group(),
                    line_number=i
                ))

    # Sanitize text: remove lines that contain critical findings or belong to injection blocks
    critical_lines = {f.line_number for f in findings if f.severity == "critical"}
    sanitized_lines = []
    removed_sections = []
    in_injection_block = False

    for i, line in enumerate(lines, 1):
        # Track injection block markers (HTML comments or explicit delimiters)
        if re.search(r'\[HIDDEN\s+INJECTION|<!--\s*\[HIDDEN', line, re.IGNORECASE):
            in_injection_block = True
            removed_sections.append(f"Removed injection block starting at line {i}")
            if '-->' in line and not line.strip().startswith('<!--'):
                in_injection_block = False
            continue

        if in_injection_block:
            if re.search(r'\[HIDDEN\s+INJECTION\s+END|-->', line, re.IGNORECASE):
                in_injection_block = False
            continue

        if i in critical_lines:
            removed_sections.append(f"Removed line {i}: suspicious content")
            continue

        # Also strip any isolated prompt override lines
        if any(re.search(pat, line, re.IGNORECASE) for pat, _, sev in INJECTION_PATTERNS if sev == "critical"):
            removed_sections.append(f"Removed line {i}: critical directive match")
            continue

        sanitized_lines.append(line)

    sanitized_text = '\n'.join(sanitized_lines)

    # Determine risk level
    critical_count = sum(1 for f in findings if f.severity == "critical")
    warning_count = sum(1 for f in findings if f.severity == "warning")

    if critical_count >= 3:
        risk_level = "critical"
    elif critical_count >= 1:
        risk_level = "high"
    elif warning_count >= 2:
        risk_level = "medium"
    elif warning_count >= 1:
        risk_level = "low"
    else:
        risk_level = "none"

    passed = risk_level in ("none", "low")

    return Stage1Result(
        passed=passed,
        findings=findings,
        risk_level=risk_level,
        sanitized_text=sanitized_text,
        original_text=text
    )

"""
Section definitions and prompt templates.

Design idea: the sections form a CHAIN. Each section is generated from the
original input PLUS the sections it depends on, so IDs and content stay
consistent (e.g. test cases are written against the user stories,
the traceability matrix links REQ -> US -> TC).
"""

SYSTEM_PROMPT = """You are a senior Business Analyst with 15+ years in Banking & Financial \
Services (UK and India): regulatory reporting, consumer credit, credit reference agency \
reporting, collections & recoveries, data warehousing (Teradata/SQL) and UAT.

You turn raw inputs (messy meeting notes, emails, or business requirement documents) into \
client-ready project documentation.

Rules:
- Write in clear, professional, client-ready British English. Concise, no filler.
- Output GitHub-flavoured Markdown only. Use '##' and '###' for headings (never '#').
- Use Markdown tables for structured data. Use ```sql and ```gherkin code fences for code.
- Never invent hard facts (system names, table names, dates, figures, regulation clauses). \
If something is not in the input, state it as an assumption marked **[Assumption]** \
or list it under open questions.
- Use stable IDs so documents cross-reference: REQ-01, US-01, DM-01, TC-01, RISK-01.
- Do not add any preamble such as "Here is..."; start directly with the content."""


# Order matters: this is the generation chain.
SECTIONS = [
    {
        "id": "analysis",
        "title": "Requirement Analysis & Executive Summary",
        "depends_on": [],
        "instructions": """Produce:
## Executive Summary (4-6 sentences: business problem, objective, expected outcome)
## Business Objectives (bullets)
## Scope (### In Scope / ### Out of Scope)
## Stakeholders (table: Stakeholder | Role | Interest / Responsibility)
## Business Requirements (table: ID | Requirement | Priority (MoSCoW) | Source)
  - Break the input into atomic requirements with IDs REQ-01, REQ-02...
## Assumptions
## Constraints & Dependencies
## Open Questions for the Business (numbered; these are gaps found in the input)""",
    },
    {
        "id": "as_is",
        "title": "Current Process (AS-IS)",
        "depends_on": ["analysis"],
        "instructions": """Describe the current state.
## Process Overview (short paragraph)
## Process Steps (table: Step | Actor | Activity | System / Tool | Output)
## Pain Points & Risks (table: # | Pain Point | Impact | Linked REQ)
## Current Data Sources & Systems (bullets)
If the input gives little detail about today's process, describe the most likely current \
state for this kind of BFSI process and mark it clearly with **[Assumption]**.""",
    },
    {
        "id": "to_be",
        "title": "Future Process (TO-BE)",
        "depends_on": ["analysis", "as_is"],
        "instructions": """Describe the target state.
## Target Process Overview
## Process Steps (table: Step | Actor | Activity | System / Tool | Control / Check)
## Key Changes from AS-IS (table: Area | AS-IS | TO-BE | Benefit)
## Business Rules (table: Rule ID | Rule | Linked REQ) - use BR-01...
## Controls & Governance (data quality, reconciliation, sign-off, audit trail)
## Expected Benefits (quantify only where the input supports it)""",
    },
    {
        "id": "user_stories",
        "title": "User Stories & Acceptance Criteria",
        "depends_on": ["analysis", "to_be"],
        "instructions": """Write user stories covering every REQ.
For each story:
### US-xx: <short title>
**Linked requirement:** REQ-xx | **Priority:** Must/Should/Could
**Story:** As a <role>, I want <capability>, so that <benefit>.
**Acceptance criteria:**
```gherkin
Scenario: ...
  Given ...
  When ...
  Then ...
```
Include at least one negative / exception scenario where relevant.
Finish with ## Definition of Done (bullets).""",
    },
    {
        "id": "data_mapping",
        "title": "Data Requirements & Source-to-Target Mapping",
        "depends_on": ["analysis", "to_be", "user_stories"],
        "instructions": """Produce:
## Data Entities in Scope (bullets with one-line description)
## Source-to-Target Mapping (table: ID | Target Field | Description | Data Type | Source System | Source Table.Column | Transformation Rule | Mandatory (Y/N) | Linked US)
  - Use IDs DM-01... Mark any guessed table/column names as [Assumption].
## Data Quality Rules (table: DQ ID | Field | Rule | Threshold | Action on Failure)
## Reference Data & Code Values (where relevant)
## Data Retention & Privacy Considerations (GDPR / DPDP Act as applicable)""",
    },
    {
        "id": "test_cases",
        "title": "Test Cases & SQL Validation",
        "depends_on": ["user_stories", "data_mapping"],
        "instructions": """Produce:
## Test Approach (short: test levels, environments, entry/exit criteria)
## UAT Test Cases (table: TC ID | Linked US | Scenario | Pre-condition | Test Steps | Expected Result | Type (Positive/Negative/Boundary))
## SQL Validation Queries
For each key check give a heading and a ```sql block (ANSI / Teradata-compatible):
  - Record count reconciliation source vs target
  - Mandatory field null checks
  - Transformation rule validation
  - Duplicate key check
  - Threshold / business rule checks
Add a one-line comment above each query explaining what a failure means.
## Defect Severity Guidelines (short table)""",
    },
    {
        "id": "hld",
        "title": "High-Level Design",
        "depends_on": ["analysis", "to_be", "data_mapping"],
        "instructions": """Produce a high-level solution design:
## Solution Overview
## Architecture Components (table: Component | Purpose | Technology [Assumption if not given])
## Data Flow (numbered steps from source to consumption/reporting)
## Interfaces & Integrations (table: Interface | Source | Target | Frequency | Format)
## Non-Functional Requirements (table: Category | Requirement) - performance, availability, security, auditability, scalability
## Security & Access Control
## Risks & Mitigations (table: RISK ID | Risk | Likelihood | Impact | Mitigation)
## Implementation Approach & Phasing
## Approvals Required (sign-off roles)""",
    },
    {
        "id": "traceability",
        "title": "Requirements Traceability Matrix",
        "depends_on": ["analysis", "user_stories", "data_mapping", "test_cases"],
        "instructions": """Produce:
## Traceability Matrix (table: REQ ID | Requirement (short) | User Story IDs | Data Mapping IDs | Test Case IDs | Coverage Status)
Coverage Status = Covered / Partially Covered / Gap.
## Coverage Summary (counts and any gaps with recommended action)
Only use IDs that actually exist in the provided sections.""",
    },
]

SECTION_BY_ID = {s["id"]: s for s in SECTIONS}


def build_section_prompt(section_id: str, context: dict, sections_content: dict) -> str:
    s = SECTION_BY_ID[section_id]
    parts = [_context_block(context)]
    for dep in s["depends_on"]:
        txt = sections_content.get(dep, "").strip()
        if txt:
            parts.append(f"=== EXISTING SECTION: {SECTION_BY_ID[dep]['title']} ===\n{txt}")
    parts.append(f"=== YOUR TASK ===\nWrite the section '{s['title']}'.\n{s['instructions']}")
    return "\n\n".join(parts)


def _context_block(ctx: dict) -> str:
    lines = [f"Project: {ctx.get('project_name') or 'Untitled'}"]
    if ctx.get("client"):
        lines.append(f"Client / Business unit: {ctx['client']}")
    if ctx.get("domain"):
        lines.append(f"Domain / regulatory context: {ctx['domain']}")
    if ctx.get("system_context"):
        lines.append(f"Known systems, tables and current process details:\n{ctx['system_context']}")
    lines.append(f"=== RAW INPUT (notes / BRD) ===\n{ctx.get('raw_input', '').strip()}")
    return "\n".join(lines)


IMPROVE_PRESETS = {
    "Make it client-ready": "Rewrite to be polished, client-ready and professional. Keep all facts, IDs, tables and structure.",
    "Fix grammar & clarity": "Fix grammar, spelling and clarity only. Do not change meaning, IDs or structure.",
    "Make it concise": "Make it more concise: remove repetition and filler while keeping every requirement, ID and table.",
    "Add more detail": "Expand with more depth and BFSI best-practice detail. Keep existing IDs; add new rows/items where useful.",
}


def build_improve_prompt(section_title: str, content: str, instruction: str) -> str:
    return f"""Improve the following section of a BFSI project document.

Section: {section_title}
User instruction: {instruction}

Keep Markdown formatting (## / ### headings, tables, ```sql / ```gherkin fences).
Return ONLY the full improved section.

=== CURRENT SECTION ===
{content}"""


# ---------------- Diagrams (Mermaid) ----------------

DIAGRAM_TYPES = {
    "AS-IS process flow": {
        "mermaid": "flowchart TD", "attach": "as_is",
        "guide": "Flowchart of the current process. Use swimlane-style subgraphs per actor. Mark pain points with a different style class.",
        "sources": ["as_is"],
    },
    "TO-BE process flow": {
        "mermaid": "flowchart TD", "attach": "to_be",
        "guide": "Flowchart of the target process with decision diamonds for checks/controls. Use subgraphs per actor.",
        "sources": ["to_be"],
    },
    "Customer journey": {
        "mermaid": "journey", "attach": "to_be",
        "guide": "Mermaid 'journey' diagram of the customer's experience across stages, with satisfaction scores 1-5 and actors.",
        "sources": ["analysis", "to_be"],
    },
    "State chart": {
        "mermaid": "stateDiagram-v2", "attach": "hld",
        "guide": "State diagram of the key business entity lifecycle (e.g. account / case / record status) with transitions labelled by events.",
        "sources": ["to_be", "data_mapping"],
    },
    "System sequence diagram": {
        "mermaid": "sequenceDiagram", "attach": "hld",
        "guide": "Sequence diagram of interactions between users, systems and interfaces in the TO-BE solution.",
        "sources": ["hld"],
    },
    "Data flow / architecture": {
        "mermaid": "flowchart LR", "attach": "hld",
        "guide": "Left-to-right data flow from source systems through staging, warehouse, controls to reports/consumers.",
        "sources": ["hld", "data_mapping"],
    },
    "Data model (ER diagram)": {
        "mermaid": "erDiagram", "attach": "data_mapping",
        "guide": "ER diagram of the key entities and relationships with main attributes.",
        "sources": ["data_mapping"],
    },
}

ATTACH_OPTIONS = {s["id"]: s["title"] for s in SECTIONS}
ATTACH_OPTIONS["appendix"] = "Appendix: Diagrams"


def build_diagram_prompt(dtype: str, extra: str, context: dict, sections_content: dict) -> str:
    d = DIAGRAM_TYPES.get(dtype)
    src_text = ""
    sources = d["sources"] if d else list(sections_content.keys())
    for sid in sources:
        if sections_content.get(sid):
            src_text += f"\n=== {SECTION_BY_ID[sid]['title']} ===\n{sections_content[sid]}\n"
    if not src_text:
        src_text = f"\n=== RAW INPUT ===\n{context.get('raw_input', '')}\n"
    header = d["mermaid"] if d else "an appropriate Mermaid diagram type"
    guide = d["guide"] if d else ""
    return f"""Create a Mermaid diagram: {dtype}.
Start with: {header}
Guidance: {guide}
Additional user instruction: {extra or 'None'}

Rules:
- Return ONLY valid Mermaid code. No code fences, no explanation.
- Keep it readable: max ~20 nodes. Short labels. Wrap labels containing special characters in double quotes.
- Do not use HTML tags or emojis. Avoid parentheses inside unquoted labels.

Source material:{src_text}"""


def build_diagram_fix_prompt(code: str, instruction: str) -> str:
    return f"""Update this Mermaid diagram.
Instruction: {instruction}
Return ONLY the full valid Mermaid code, no fences or explanation.

{code}"""

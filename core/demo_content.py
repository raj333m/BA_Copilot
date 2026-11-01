"""
Demo mode content: a realistic (fictional) UK consumer-credit example so the app
can be demonstrated end-to-end without an API key. All names are illustrative.
"""

SAMPLE_INPUT = """Mtg notes - 14 Oct - Collections / Credit Reporting / DW team

- collections ops raised: customers on a payment arrangement are still showing as "in arrears" on the monthly credit reference agency (CRA) file. complaints going up, 23 last month. Consumer Duty risk flagged by Compliance.
- arrangement data sits in the collections system (CollectPro). DW does not currently take the arrangement table, only arrears balance + days past due.
- CRA file built monthly from DW (credit reporting mart). Status code logic is in the DW ETL.
- need: new arrangement indicator + arrangement start/end date in DW, feed into CRA status logic -> arrangement accounts reported with the arrangement flag, not just arrears status.
- if arrangement broken (2 missed payments) should revert to arrears reporting.
- want DQ checks before file goes out - counts recon DW vs file, no nulls in mandatory fields, flag mismatches.
- ops want an exceptions report / dashboard each month before submission. sign-off by credit reporting lead.
- historic correction? TBC - compliance to confirm if past 6 months need amendments.
- target: Q1 next year. products in scope: personal loans + credit cards. mortgages out of scope for now.
"""

SAMPLE_CONTEXT = {
    "project_name": "CRA Arrangement Reporting Remediation",
    "client": "Retail Bank - Credit Reporting & Collections",
    "domain": "UK Consumer Credit - CRA reporting / FCA Consumer Duty",
    "system_context": "Collections system: CollectPro (arrangement table). Data warehouse: credit reporting mart (Teradata). Monthly CRA file produced by DW ETL.",
}

DEMO_SECTIONS = {
"analysis": """## Executive Summary
Customers who have agreed a payment arrangement with Collections are currently reported to the credit reference agencies (CRAs) as being in arrears, because the data warehouse (DW) does not receive arrangement data from the collections system. This causes inaccurate credit files, a rising number of complaints (23 last month) and a potential Consumer Duty breach. This initiative will source arrangement data into the DW, apply arrangement-aware status logic to the monthly CRA file, and add pre-submission data quality controls and an exceptions report. The target go-live is Q1, covering personal loans and credit cards.

## Business Objectives
- Report customers on an active payment arrangement accurately to the CRAs.
- Reduce arrangement-related credit file complaints.
- Demonstrate good customer outcomes under FCA Consumer Duty.
- Introduce auditable data quality controls and sign-off before each CRA submission.

## Scope
### In Scope
- Personal loans and credit cards.
- Sourcing arrangement indicator, start date and end date from CollectPro into the DW.
- Changes to CRA status derivation logic in the DW ETL.
- Pre-submission data quality checks and monthly exceptions report.

### Out of Scope
- Mortgages (future phase).
- Changes to the CollectPro arrangement process itself.
- Historic corrections (pending Compliance decision — see Open Questions).

## Stakeholders
| Stakeholder | Role | Interest / Responsibility |
|---|---|---|
| Collections Operations | Business owner of arrangements | Accurate arrangement data; fewer complaints |
| Credit Reporting Lead | Approver | Monthly file sign-off |
| Compliance | Oversight | Consumer Duty and CRA reporting obligations |
| DW / Data Engineering | Delivery | Data sourcing, ETL changes |
| Business Analyst | Delivery | Requirements, mapping, UAT |

## Business Requirements
| ID | Requirement | Priority | Source |
|---|---|---|---|
| REQ-01 | Source arrangement indicator, start date and end date from CollectPro into the DW | Must | Mtg 14 Oct |
| REQ-02 | Report accounts on an active arrangement with the arrangement flag in the CRA file | Must | Mtg 14 Oct |
| REQ-03 | Revert to arrears reporting when an arrangement is broken (2 missed payments) | Must | Mtg 14 Oct |
| REQ-04 | Reconcile record counts between DW and the CRA file before submission | Must | Mtg 14 Oct |
| REQ-05 | Validate mandatory fields are not null before submission | Must | Mtg 14 Oct |
| REQ-06 | Produce a monthly exceptions report for Ops review before submission | Should | Mtg 14 Oct |
| REQ-07 | Capture Credit Reporting Lead sign-off before file release | Must | Mtg 14 Oct |

## Assumptions
- **[Assumption]** CollectPro holds one active arrangement per account at any point in time.
- **[Assumption]** "Broken" is defined as two consecutive missed arrangement payments.
- **[Assumption]** The CRA file layout already supports an arrangement flag value.

## Constraints & Dependencies
- Go-live required in Q1.
- Dependent on CollectPro extract availability and DW release calendar.
- Historic correction scope depends on a Compliance decision.

## Open Questions for the Business
1. Do the last 6 months of CRA submissions need amendment? (Compliance)
2. Are "2 missed payments" consecutive or cumulative?
3. How should arrangements with an end date in the past but no closure status be treated?
4. Who is the backup approver if the Credit Reporting Lead is unavailable?
5. What is the tolerance (if any) for count reconciliation differences?""",

"as_is": """## Process Overview
Each month, the DW ETL derives CRA account status using arrears balance and days past due (DPD) only. Arrangement data held in CollectPro is not sourced, so arrangement customers are reported as in arrears. The file is submitted without a structured data quality or exceptions review.

## Process Steps
| Step | Actor | Activity | System / Tool | Output |
|---|---|---|---|---|
| 1 | Collections Ops | Agree payment arrangement with customer | CollectPro | Arrangement record |
| 2 | DW ETL | Load arrears balance and DPD | Credit reporting mart | Account arrears data |
| 3 | DW ETL | Derive CRA status from DPD only | Credit reporting mart | Status codes |
| 4 | DW ETL | Generate monthly CRA file | Credit reporting mart | CRA file |
| 5 | Credit Reporting | Submit file to CRAs | File transfer | Submission |
| 6 | Customer / Complaints | Customer sees arrears on credit file and complains | Complaints system | Complaint |

## Pain Points & Risks
| # | Pain Point | Impact | Linked REQ |
|---|---|---|---|
| 1 | Arrangement data not in DW | Inaccurate CRA reporting | REQ-01, REQ-02 |
| 2 | Status logic ignores arrangements | Customer detriment, Consumer Duty risk | REQ-02, REQ-03 |
| 3 | No count reconciliation | Incomplete submissions go undetected | REQ-04 |
| 4 | No mandatory field checks | Rejected or inaccurate records | REQ-05 |
| 5 | No exceptions review or formal sign-off | Weak audit trail | REQ-06, REQ-07 |

## Current Data Sources & Systems
- CollectPro (collections system) — arrangement table **not** sourced.
- Credit reporting mart (Teradata) — arrears balance, DPD, account attributes.
- Monthly CRA file generated by DW ETL.""",

"to_be": """## Target Process Overview
Arrangement data is sourced daily from CollectPro into the DW. At month end, CRA status derivation checks for an active arrangement before applying arrears logic. Automated data quality checks run before file generation, an exceptions report is reviewed by Ops, and the Credit Reporting Lead signs off before submission.

## Process Steps
| Step | Actor | Activity | System / Tool | Control / Check |
|---|---|---|---|---|
| 1 | Collections Ops | Agree / update arrangement | CollectPro | Mandatory dates captured |
| 2 | DW ETL | Load arrangement indicator, start and end dates | Credit reporting mart | Load count reconciliation |
| 3 | DW ETL | Derive CRA status: arrangement check first, then DPD | Credit reporting mart | BR-01 to BR-03 |
| 4 | DW ETL | Run DQ checks | Credit reporting mart | DQ-01 to DQ-04 |
| 5 | Collections Ops | Review exceptions report | BI dashboard | Exceptions resolved or accepted |
| 6 | Credit Reporting Lead | Sign off file | Sign-off log | Approval recorded |
| 7 | Credit Reporting | Submit file to CRAs | File transfer | Submission receipt retained |

## Key Changes from AS-IS
| Area | AS-IS | TO-BE | Benefit |
|---|---|---|---|
| Data | No arrangement data in DW | Arrangement fields sourced daily | Complete customer view |
| Status logic | DPD only | Arrangement-aware | Accurate credit files |
| Controls | None | Automated DQ + exceptions report | Fewer reporting errors |
| Governance | Informal | Recorded sign-off | Audit trail |

## Business Rules
| Rule ID | Rule | Linked REQ |
|---|---|---|
| BR-01 | If arrangement is active at month end, report arrangement flag | REQ-02 |
| BR-02 | If arrangement is broken (2 missed payments), report arrears status from DPD | REQ-03 |
| BR-03 | If arrangement end date has passed and account is up to date, report as up to date | REQ-02 |
| BR-04 | File must not be released without recorded sign-off | REQ-07 |

## Controls & Governance
- Count reconciliation between DW population and CRA file.
- Null checks on mandatory fields.
- Exceptions report reviewed and evidenced by Ops.
- Sign-off recorded with approver, date and file version.

## Expected Benefits
- Accurate reporting for customers on arrangements.
- Reduction in related complaints (baseline: 23 last month).
- Evidence of good outcomes for Consumer Duty.""",

"user_stories": """### US-01: Source arrangement data into the DW
**Linked requirement:** REQ-01 | **Priority:** Must
**Story:** As a Credit Reporting Analyst, I want arrangement indicator, start date and end date available in the DW, so that CRA status can reflect arrangements.
**Acceptance criteria:**
```gherkin
Scenario: Active arrangement loaded
  Given an account has an active arrangement in CollectPro
  When the daily DW load completes
  Then the account shows arrangement_ind = 'Y' with start and end dates populated

Scenario: Arrangement missing start date
  Given an arrangement record has no start date
  When the DW load runs
  Then the record is written to the load exceptions table
```

### US-02: Report active arrangements to CRAs
**Linked requirement:** REQ-02 | **Priority:** Must
**Story:** As a customer on a payment arrangement, I want my credit file to show the arrangement, so that I am not reported as simply in arrears.
**Acceptance criteria:**
```gherkin
Scenario: Active arrangement at month end
  Given an account has an active arrangement on the reporting date
  When the CRA file is generated
  Then the account is reported with the arrangement flag
```

### US-03: Revert broken arrangements to arrears
**Linked requirement:** REQ-03 | **Priority:** Must
**Story:** As a Credit Reporting Lead, I want broken arrangements reported from arrears status, so that reporting stays accurate.
**Acceptance criteria:**
```gherkin
Scenario: Arrangement broken
  Given an account has missed 2 arrangement payments
  When the CRA file is generated
  Then the status is derived from days past due and no arrangement flag is reported
```

### US-04: Pre-submission data quality checks
**Linked requirement:** REQ-04, REQ-05 | **Priority:** Must
**Story:** As a Credit Reporting Analyst, I want automated count and null checks, so that incomplete files are caught before submission.
**Acceptance criteria:**
```gherkin
Scenario: Count mismatch
  Given the DW population is 120,000 accounts
  When the CRA file contains 119,950 records
  Then the DQ check fails and the file is blocked
```

### US-05: Monthly exceptions report and sign-off
**Linked requirement:** REQ-06, REQ-07 | **Priority:** Should
**Story:** As a Collections Ops Manager, I want an exceptions report before submission, so that issues are resolved and sign-off is evidenced.
**Acceptance criteria:**
```gherkin
Scenario: Sign-off recorded
  Given the exceptions report has been reviewed
  When the Credit Reporting Lead approves the file
  Then approver name, timestamp and file version are stored in the sign-off log
```

## Definition of Done
- Acceptance criteria passed in UAT.
- DQ checks automated and evidenced.
- Mapping document and runbook updated.
- Business sign-off obtained.""",

"data_mapping": """## Data Entities in Scope
- **Account** — personal loan and credit card accounts reported to CRAs.
- **Arrangement** — payment arrangement agreed in CollectPro.
- **CRA Submission** — monthly file record per account.

## Source-to-Target Mapping
| ID | Target Field | Description | Data Type | Source System | Source Table.Column | Transformation Rule | Mandatory | Linked US |
|---|---|---|---|---|---|---|---|---|
| DM-01 | arrangement_ind | Active arrangement flag | CHAR(1) | CollectPro | arrangement.status **[Assumption]** | 'Y' if status = ACTIVE else 'N' | Y | US-01 |
| DM-02 | arrangement_start_dt | Arrangement start date | DATE | CollectPro | arrangement.start_date **[Assumption]** | Direct | Y | US-01 |
| DM-03 | arrangement_end_dt | Arrangement end date | DATE | CollectPro | arrangement.end_date **[Assumption]** | Direct; NULL if open-ended | N | US-01 |
| DM-04 | missed_arr_pmts | Missed arrangement payments | SMALLINT | CollectPro | arrangement.missed_count **[Assumption]** | Direct | Y | US-03 |
| DM-05 | cra_status_cd | CRA status code | CHAR(2) | DW | Derived | Apply BR-01 to BR-03 | Y | US-02, US-03 |
| DM-06 | cra_arrangement_flag | Arrangement flag in CRA file | CHAR(1) | DW | Derived | 'A' if BR-01 applies else blank | N | US-02 |

## Data Quality Rules
| DQ ID | Field | Rule | Threshold | Action on Failure |
|---|---|---|---|---|
| DQ-01 | All records | DW count = CRA file count | 0 difference | Block file |
| DQ-02 | cra_status_cd | Not null | 0 nulls | Block file |
| DQ-03 | arrangement_start_dt | Not null when arrangement_ind = 'Y' | 0 nulls | Exceptions report |
| DQ-04 | arrangement_end_dt | Must be >= start date | 0 failures | Exceptions report |

## Reference Data & Code Values
- arrangement_ind: Y / N
- cra_arrangement_flag: A (arrangement) / blank

## Data Retention & Privacy Considerations
- Arrangement data is personal and potentially sensitive financial data; access restricted to authorised roles.
- Retain in line with bank retention policy and UK GDPR.""",

"test_cases": """## Test Approach
System testing by DW team, followed by UAT with Credit Reporting and Collections Ops using a masked production-like dataset. Entry criteria: build deployed, test data loaded. Exit criteria: all Must test cases passed, no open Severity 1/2 defects.

## UAT Test Cases
| TC ID | Linked US | Scenario | Pre-condition | Test Steps | Expected Result | Type |
|---|---|---|---|---|---|---|
| TC-01 | US-01 | Active arrangement loaded | Active arrangement in CollectPro | Run DW load | arrangement_ind = 'Y', dates populated | Positive |
| TC-02 | US-01 | Missing start date | Arrangement with null start date | Run DW load | Record in exceptions table | Negative |
| TC-03 | US-02 | Active arrangement reported | Active arrangement at month end | Generate CRA file | Arrangement flag = 'A' | Positive |
| TC-04 | US-03 | Broken arrangement | 2 missed payments | Generate CRA file | Status from DPD, no flag | Positive |
| TC-05 | US-03 | 1 missed payment | 1 missed payment | Generate CRA file | Arrangement flag retained | Boundary |
| TC-06 | US-04 | Count mismatch | Remove 50 records from file | Run DQ | DQ-01 fails, file blocked | Negative |
| TC-07 | US-05 | Sign-off captured | Exceptions reviewed | Approve file | Sign-off log populated | Positive |

## SQL Validation Queries
### Count reconciliation (DQ-01)
-- Failure means the file is incomplete or has duplicates.
```sql
SELECT dw.cnt AS dw_count, f.cnt AS file_count, dw.cnt - f.cnt AS difference
FROM (SELECT COUNT(*) AS cnt FROM cr_mart.account_month WHERE report_dt = DATE '2027-01-31') dw
CROSS JOIN (SELECT COUNT(*) AS cnt FROM cr_mart.cra_file_stage WHERE report_dt = DATE '2027-01-31') f;
```

### Mandatory field null check (DQ-02)
-- Any rows returned must be fixed before submission.
```sql
SELECT account_id FROM cr_mart.cra_file_stage
WHERE report_dt = DATE '2027-01-31' AND cra_status_cd IS NULL;
```

### Arrangement rule validation (BR-01)
-- Rows returned are active arrangements not flagged in the file.
```sql
SELECT a.account_id
FROM cr_mart.account_month a
JOIN cr_mart.cra_file_stage f ON a.account_id = f.account_id AND a.report_dt = f.report_dt
WHERE a.report_dt = DATE '2027-01-31'
  AND a.arrangement_ind = 'Y' AND a.missed_arr_pmts < 2
  AND COALESCE(f.cra_arrangement_flag, '') <> 'A';
```

### Duplicate key check
-- Each account must appear once per reporting month.
```sql
SELECT account_id, COUNT(*) FROM cr_mart.cra_file_stage
WHERE report_dt = DATE '2027-01-31'
GROUP BY account_id HAVING COUNT(*) > 1;
```

## Defect Severity Guidelines
| Severity | Definition |
|---|---|
| 1 - Critical | Incorrect customer reporting; blocks submission |
| 2 - High | Control failure with workaround |
| 3 - Medium | Report/presentation issue |
| 4 - Low | Cosmetic |""",

"hld": """## Solution Overview
Extend the credit reporting mart with arrangement data from CollectPro, embed arrangement-aware status rules in the CRA ETL, and add a control layer (DQ checks, exceptions report, sign-off log) before file release.

## Architecture Components
| Component | Purpose | Technology |
|---|---|---|
| CollectPro extract | Daily arrangement feed | Flat file / DB extract **[Assumption]** |
| Staging layer | Land and validate raw feed | Teradata staging |
| Credit reporting mart | Integrated account + arrangement data | Teradata |
| CRA status engine | Apply BR-01 to BR-03 | DW ETL |
| DQ control framework | Run DQ-01 to DQ-04, block on failure | SQL / ETL |
| Exceptions dashboard | Ops review | Power BI **[Assumption]** |
| Sign-off log | Approval audit trail | DW table |

## Data Flow
1. CollectPro produces daily arrangement extract.
2. Extract lands in staging; load counts reconciled.
3. Arrangement data merged into the credit reporting mart.
4. At month end, CRA status engine derives status and arrangement flag.
5. DQ framework runs; failures block file generation.
6. Exceptions dashboard refreshed for Ops review.
7. Credit Reporting Lead signs off; file released to CRAs.

## Interfaces & Integrations
| Interface | Source | Target | Frequency | Format |
|---|---|---|---|---|
| Arrangement feed | CollectPro | DW staging | Daily | Delimited file **[Assumption]** |
| CRA file | DW | CRAs | Monthly | CRA layout |
| Exceptions report | DW | Power BI | Monthly | Table / view |

## Non-Functional Requirements
| Category | Requirement |
|---|---|
| Performance | Month-end CRA build completes within existing batch window |
| Availability | Daily feed SLA by 06:00 |
| Security | Role-based access to arrangement data |
| Auditability | DQ results and sign-off retained for 7 years **[Assumption]** |
| Scalability | Supports adding mortgages in a later phase |

## Security & Access Control
- Arrangement data classified as confidential; least-privilege access.
- Sign-off restricted to named approvers.

## Risks & Mitigations
| RISK ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| RISK-01 | CollectPro data quality issues | Medium | High | Load-level DQ and exceptions table |
| RISK-02 | Historic correction scope unclear | High | Medium | Early Compliance decision |
| RISK-03 | Q1 date at risk due to release calendar | Medium | High | Book release slot now |

## Implementation Approach & Phasing
- Phase 1: Sourcing + status logic + DQ (Q1).
- Phase 2: Historic corrections (if required) and mortgages.

## Approvals Required
- Credit Reporting Lead, Head of Collections Ops, Compliance, DW Design Authority.""",

"traceability": """## Traceability Matrix
| REQ ID | Requirement (short) | User Story IDs | Data Mapping IDs | Test Case IDs | Coverage Status |
|---|---|---|---|---|---|
| REQ-01 | Source arrangement data | US-01 | DM-01, DM-02, DM-03, DM-04 | TC-01, TC-02 | Covered |
| REQ-02 | Report arrangement flag | US-02 | DM-05, DM-06 | TC-03 | Covered |
| REQ-03 | Revert broken arrangements | US-03 | DM-04, DM-05 | TC-04, TC-05 | Covered |
| REQ-04 | Count reconciliation | US-04 | — | TC-06 | Covered |
| REQ-05 | Mandatory null checks | US-04 | — | — | Partially Covered |
| REQ-06 | Exceptions report | US-05 | — | — | Gap |
| REQ-07 | Sign-off before release | US-05 | — | TC-07 | Covered |

## Coverage Summary
- 7 requirements: 5 Covered, 1 Partially Covered, 1 Gap.
- **Action:** add a UAT test case for DQ-02 null check (REQ-05) and for exceptions report content (REQ-06).""",
}

DEMO_DIAGRAMS = {
"AS-IS process flow": """flowchart TD
    subgraph Collections
        A[Agree payment arrangement] --> B[(CollectPro)]
    end
    subgraph DataWarehouse
        C[Load arrears and DPD] --> D[Derive status from DPD only]
        D --> E[Generate CRA file]
    end
    subgraph CreditReporting
        E --> F[Submit to CRAs]
    end
    B -. not sourced .-> C
    F --> G[Customer sees arrears]
    G --> H[Complaint raised]
    classDef pain fill:#fde2e1,stroke:#c0392b;
    class D,G,H pain""",

"TO-BE process flow": """flowchart TD
    A[Agree or update arrangement in CollectPro] --> B[Daily load to DW]
    B --> C{Load counts reconcile?}
    C -- No --> X[Load exceptions table]
    C -- Yes --> D[Month-end status derivation]
    D --> E{Active arrangement?}
    E -- Yes --> F{2 or more missed payments?}
    F -- No --> G[Report arrangement flag]
    F -- Yes --> H[Report status from DPD]
    E -- No --> H
    G --> I[Run DQ checks]
    H --> I
    I --> J{DQ passed?}
    J -- No --> K[Block file and fix]
    J -- Yes --> L[Ops review exceptions report]
    L --> M[Credit Reporting Lead sign-off]
    M --> N[Submit file to CRAs]""",

"Customer journey": """journey
    title Customer on a payment arrangement
    section Financial difficulty
      Contacts bank for help: 3: Customer
      Agrees arrangement: 4: Customer, Collections
    section Reporting
      Arrangement reported to CRAs: 4: Bank
      Checks credit file: 4: Customer
    section Outcome
      Sees accurate arrangement status: 5: Customer
      No complaint needed: 5: Customer""",

"State chart": """stateDiagram-v2
    [*] --> UpToDate
    UpToDate --> InArrears: Payment missed
    InArrears --> OnArrangement: Arrangement agreed
    OnArrangement --> UpToDate: Arrangement completed
    OnArrangement --> Broken: 2 missed payments
    Broken --> InArrears: Revert to DPD reporting
    InArrears --> UpToDate: Arrears cleared
    UpToDate --> [*]: Account closed""",

"System sequence diagram": """sequenceDiagram
    participant CP as CollectPro
    participant STG as DW Staging
    participant MART as Credit Reporting Mart
    participant DQ as DQ Framework
    participant BI as Exceptions Dashboard
    participant LEAD as Credit Reporting Lead
    participant CRA as CRAs
    CP->>STG: Daily arrangement extract
    STG->>MART: Validated load
    MART->>MART: Month-end status derivation
    MART->>DQ: Run DQ-01 to DQ-04
    DQ-->>MART: Pass or block
    MART->>BI: Refresh exceptions
    BI->>LEAD: Review and sign-off request
    LEAD-->>MART: Approval logged
    MART->>CRA: Submit monthly file""",

"Data flow / architecture": """flowchart LR
    A[(CollectPro)] --> B[Staging]
    Z[(Account and arrears data)] --> C
    B --> C[(Credit Reporting Mart)]
    C --> D[CRA Status Engine]
    D --> E[DQ Control Framework]
    E -- pass --> F[CRA File]
    E -- fail --> G[Blocked and Alert]
    C --> H[Exceptions Dashboard]
    H --> I[Sign-off Log]
    I --> F
    F --> J[Credit Reference Agencies]""",

"Data model (ER diagram)": """erDiagram
    ACCOUNT ||--o{ ARRANGEMENT : has
    ACCOUNT ||--o{ CRA_SUBMISSION : reported_in
    CRA_SUBMISSION }o--|| SIGNOFF_LOG : approved_by
    ACCOUNT {
        string account_id
        string product_type
        int days_past_due
        decimal arrears_balance
    }
    ARRANGEMENT {
        string arrangement_id
        string account_id
        date start_date
        date end_date
        int missed_count
    }
    CRA_SUBMISSION {
        string account_id
        date report_dt
        string cra_status_cd
        string cra_arrangement_flag
    }
    SIGNOFF_LOG {
        string file_version
        string approver
        datetime approved_at
    }""",
}

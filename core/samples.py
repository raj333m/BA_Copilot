"""Six BFSI test examples (fictional) in different input styles."""
SAMPLES = [
 {
  "key": "cra",
  "label": "CRA arrangement reporting",
  "region": "UK",
  "kind": "Meeting notes",
  "meta": {
   "project_name": "CRA Arrangement Reporting Remediation",
   "client": "Retail Bank - Credit Reporting & Collections",
   "version": "0.1",
   "doc_title": "Business Requirements & High-Level Design",
   "domain": "UK Consumer Credit - CRA reporting / FCA Consumer Duty",
   "system_context": "Collections system: CollectPro (arrangement table). Data warehouse: credit reporting mart (Teradata). Monthly CRA file produced by DW ETL."
  },
  "notes": "Mtg notes - 14 Oct - Collections / Credit Reporting / DW team\n\n- collections ops raised: customers on a payment arrangement are still showing as \"in arrears\" on the monthly credit reference agency (CRA) file. complaints going up, 23 last month. Consumer Duty risk flagged by Compliance.\n- arrangement data sits in the collections system (CollectPro). DW does not currently take the arrangement table, only arrears balance + days past due.\n- CRA file built monthly from DW (credit reporting mart). Status code logic is in the DW ETL.\n- need: new arrangement indicator + arrangement start/end date in DW, feed into CRA status logic -> arrangement accounts reported with the arrangement flag, not just arrears status.\n- if arrangement broken (2 missed payments) should revert to arrears reporting.\n- want DQ checks before file goes out - counts recon DW vs file, no nulls in mandatory fields, flag mismatches.\n- ops want an exceptions report / dashboard each month before submission. sign-off by credit reporting lead.\n- historic correction? TBC - compliance to confirm if past 6 months need amendments.\n- target: Q1 next year. products in scope: personal loans + credit cards. mortgages out of scope for now."
 },
 {
  "key": "rekyc",
  "label": "Periodic KYC update (Re-KYC)",
  "region": "India",
  "kind": "Email thread",
  "meta": {
   "project_name": "Periodic KYC Updation Automation",
   "client": "Private Sector Bank - Retail Liabilities & Compliance",
   "version": "0.1",
   "doc_title": "Business Requirements & High-Level Design",
   "domain": "India - RBI KYC Master Direction / AML",
   "system_context": "Core banking: Finacle (CIF master). CKYCR upload via existing CKYC adaptor. Customer comms through SMS/email gateway and mobile app push. Reporting from enterprise data warehouse (Oracle)."
  },
  "notes": "From: Head - Retail Ops\nTo: Compliance; IT Apps; BA team\nSubject: RE: RE: Re-KYC backlog - need a proper fix this quarter\n\nTeam - we have ~4.2 lakh customers overdue for periodic KYC update. Branches are calling customers manually off an Excel list that MIS sends every Monday. Audit flagged it again last week.\n\n> From Compliance: Reminder that periodic updation is risk-based - high risk every 2 yrs, medium every 8, low every 10 (per RBI KYC MD). Due date must be computed from last KYC date + risk category, not account open date (current MIS uses open date, which is wrong).\n\n> From IT Apps: Risk category is in Finacle CIF master but ~6% of CIFs have it blank. Last KYC date field is also not reliably populated for migrated accounts (pre-2015).\n\nAsks from business:\n1. auto-identify customers due in next 90 days + overdue\n2. send reminders at T-90, T-30, T-7 via SMS/email/app; stop once updated\n3. \"no change\" self-declaration through app/net banking for low risk customers where nothing changed\n4. if still not done X days after due date -> partial freeze of debits (Compliance to confirm X and exact wording, don't hardcode)\n5. dashboard for ops: due / overdue / completed by branch, region, risk category\n6. upload updated records to CKYCR\n\nAlso - senior citizens and NRIs need a branch-assisted route, not app only. Go-live before March audit if possible. Who owns the blank risk category clean-up? not agreed yet."
 },
 {
  "key": "vuln",
  "label": "Vulnerable customer flag in collections",
  "region": "UK",
  "kind": "Dictation transcript",
  "meta": {
   "project_name": "Vulnerability-Aware Collections Strategy",
   "client": "Retail Bank - Collections & Recoveries",
   "version": "0.1",
   "doc_title": "Business Requirements & High-Level Design",
   "domain": "UK - FCA Consumer Duty / FG21/1 vulnerable customers",
   "system_context": "Dialler: auto-dialler fed by nightly strategy file. Collections workflow: CollectPro. Customer vulnerability notes currently free text in CRM (Dynamics). DW: collections mart."
  },
  "notes": "ok so this is my dictation from the call with Sarah from collections strategy and the vulnerable customers team, um, Tuesday afternoon.\n\nso the problem is when an agent records that a customer is vulnerable, like bereavement or mental health or they've lost their job, it just goes in as a free text note in the CRM and nothing downstream picks it up. so the dialler keeps calling them at the same frequency as everyone else and the letters go out in the standard tone. we had two complaints escalated to the ombudsman last quarter about exactly this.\n\nwhat they want is a structured vulnerability flag with a type, a severity maybe low medium high, a review date, and who recorded it. customer consent to record it is important, Sarah was very clear, we need consent captured.\n\nthen the collections strategy should use the flag, so for high severity no outbound dialler calls, specialist team only, reduce contact frequency, pause fees and charges for thirty days, actually she said sixty, need to confirm. letters should switch to the supportive template.\n\nflags should expire at the review date unless someone renews it, and there should be a report for the vulnerable customers team showing flags due for review and how many contacts were made with flagged customers.\n\ndata protection said it's special category data for health related ones so access needs to be restricted, only collections and the vulnerability team. oh and they want MI for the board quarterly, outcomes for vulnerable versus non vulnerable customers. that's it I think. timeline is phase one by end of Q2."
 },
 {
  "key": "ifrs9",
  "label": "IFRS 9 ECL staging data feed",
  "region": "Global",
  "kind": "BRD extract",
  "meta": {
   "project_name": "IFRS 9 Staging Data Feed Enhancement",
   "client": "Group Finance - Credit Risk Reporting",
   "version": "0.1",
   "doc_title": "Business Requirements & High-Level Design",
   "domain": "IFRS 9 impairment / ECL - credit risk data",
   "system_context": "Source: loan origination system, card platform, collections mart. Target: ECL engine input feed (monthly, CSV via SFTP). DW: Teradata risk mart. Current SICR logic held in an Excel macro owned by Credit Risk."
  },
  "notes": "BUSINESS REQUIREMENTS DOCUMENT (EXTRACT) - DRAFT v0.3\n\n1. Background\nThe monthly ECL engine input is prepared partly by hand. Stage allocation (Stage 1 / 2 / 3) is computed in an Excel macro using days past due and a lifetime PD comparison supplied by the models team. Last two quarter-ends the feed was delivered late (WD+6 against a WD+3 target) and external audit raised a finding on lack of controls and lineage.\n\n2. Objectives\n- Move stage allocation logic into the risk mart so it is automated, repeatable and auditable.\n- Deliver the ECL input feed by WD+3.\n- Full lineage from source to feed for each account.\n\n3. Requirements (as provided by Credit Risk)\n3.1 Stage 3 if 90+ DPD or credit-impaired flag (default, forbearance with financial difficulty, insolvency).\n3.2 Stage 2 if significant increase in credit risk: 30+ DPD backstop, OR lifetime PD at reporting date > 2.5x origination lifetime PD (threshold to be confirmed by Model Risk), OR on watchlist.\n3.3 Otherwise Stage 1.\n3.4 Cure / probation: account to remain in Stage 2 for 3 consecutive months after criteria no longer met before moving to Stage 1 (TBC).\n3.5 Feed fields: account id, product, segment, balance, EAD, stage, stage reason code, origination PD, current PD, DPD, forbearance flag.\n3.6 Reconciliation of feed balances to General Ledger by product within tolerance (tolerance TBC by Finance).\n3.7 Stage movement report month on month (stage 1->2, 2->3, cures) for the Impairment Committee.\n\n4. Open points\n- Origination PD missing for ~3% of legacy card accounts - fallback approach not agreed.\n- Who signs off the feed each month - Finance or Credit Risk?"
 },
 {
  "key": "aml",
  "label": "AML alert tuning (false positives)",
  "region": "UK / EU",
  "kind": "Workshop notes",
  "meta": {
   "project_name": "Transaction Monitoring Alert Optimisation",
   "client": "Financial Crime Compliance - Transaction Monitoring",
   "version": "0.1",
   "doc_title": "Business Requirements & High-Level Design",
   "domain": "AML / Financial Crime - transaction monitoring",
   "system_context": "TM platform: rules-based vendor system with scenario thresholds. Case management: separate tool. Customer risk rating from KYC platform. Data feeds from core banking and payments hub, via DW."
  },
  "notes": "Workshop - TM alert optimisation - FCC Ops, TM Analytics, IT, BA\nWhiteboard capture (tidy later!)\n\nPROBLEMS\n* ~11k alerts/month, 97%+ closed as false positive. analysts overloaded, SLA breaches (target close in 30 days)\n* same customer alerting repeatedly for same pattern e.g. salary + rent every month\n* thresholds same for all segments - students vs SME vs HNW all treated alike\n* customer risk rating not used by scenarios at all\n\nIDEAS / ASKS\n* segment-based thresholds (retail low/med/high risk, SME, HNW) - analytics to propose values, NOT BA\n* below-the-line testing before any threshold change - regulator expects evidence\n* suppression of repeat alerts if previously closed as FP with same pattern within 90d, BUT never for high risk customers\n* alert scoring/prioritisation so high-risk alerts go to top of queue\n* every tuning change needs model governance sign-off + documented rationale + audit trail\n* MI: alerts by scenario, FP rate, SAR conversion rate, ageing, by segment\n\nCONCERNS\n* compliance: cannot reduce effectiveness - track SAR conversion before/after\n* data quality on customer segment ~ some SMEs coded as retail\n* IT: vendor system supports per-segment thresholds but not scoring natively - may need DW-side scoring\n\nNEXT: BA to write reqs + HLD, analytics to start BTL testing on 2 scenarios first (cash deposits, rapid movement of funds)"
 },
 {
  "key": "upi",
  "label": "UPI failed transaction reconciliation",
  "region": "India",
  "kind": "Ops escalation notes",
  "meta": {
   "project_name": "UPI Failed Transaction Reconciliation & Auto-Reversal",
   "client": "Payments Operations - Digital Banking",
   "version": "0.1",
   "doc_title": "Business Requirements & High-Level Design",
   "domain": "India - UPI / NPCI dispute handling, RBI TAT framework",
   "system_context": "UPI switch (in-house). NPCI settlement and raw files daily. Core banking: Finacle. Complaint system: CRM. Recon currently via SQL scripts + Excel on a shared drive."
  },
  "notes": "Payments ops escalation - notes from call with Head Payments Ops, Recon team lead, Customer Service, IT (switch team)\n\n- Customers debited but beneficiary not credited (deemed / failed txns). Recon team matching switch logs vs NPCI raw files vs CBS manually in Excel. ~2,500 exceptions/day at peak, festive season worse.\n- RBI TAT framework says auto-reversal within T+1 for failed UPI txns, compensation per day of delay beyond that - we paid compensation for ~1,100 cases last month. Big cost + complaints.\n- Need: automated 3-way recon - switch vs NPCI vs CBS - daily, by RRN (UPI ref no). Categories: success, failed-debited (reverse), deemed (wait for NPCI status), duplicate.\n- Auto-reversal to customer account for confirmed failed-debited, with SMS. Manual queue for anything ambiguous.\n- Ageing buckets + TAT breach alert before T+1 cut-off, so ops can act.\n- Compensation calc: auto-compute where TAT breached, credit customer, report.\n- Link to CRM so CS agents can see recon status when customer calls instead of raising a new complaint.\n- Daily MIS: volumes, exceptions by reason, reversals done, TAT breaches, compensation paid.\n- IT says NPCI files sometimes arrive late / multiple cycles per day - design must handle multiple settlement cycles.\n- Audit trail for every reversal (who/what/when). Maker-checker for manual reversals above a limit (limit TBD by Ops head)."
 }
]

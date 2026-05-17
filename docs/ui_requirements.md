# Healthcare.AI UI Specification
> Information for AI Tool to understand the ui reuirements, user base, ideas, researches, layout and design needed for this project
> Then make a not very complex but medical-grade AI UI with this information and references help 

## Target COnsumer Specific

- for Healthcare professionals, so should be Medical-grade AI UI
- must prioritize trust, scannability, and seamless clinical workflow integration
- Healthcare professionals suffer from alarm fatigue and cognitive overload
- they do not want a casual, consumer-style conversational chat app.
- Take reference from Optum’s Clinical Assistant and their "Ask AI" frameworks (https://business.optum.com/en/operations-technology/clinical-decision-support/clinical-assistant.html)
- layout must focus on strict information hierarchy, explicit provenance (sourcing), and immediate split-second utility

### References

- https://dribbble.com/shots/27330750-AI-Clinical-Assistant-UI-Healthcare-SaaS-Prompt-Interface
- https://profiles.stanford.edu/nigam-shah?tab=research-and-scholarship
- https://fuselabcreative.com/healthcare-ux-design-best-practices-guide/
- think like him - https://getmereferred.com/job-listing/senior-ux-designer-ai-ic-optum-chennai-5-to-10-years-experience-a24f4c71-0589-457b-81c2-e3a11ad95232

---

## The Structural Layout (Split-Pane Dashboard)

- Do not use a centered, single-column chat bubble design. 
- Instead, implement a three-pane workspace optimized for rapid reading:
   - Left Rail (Active Guidelines Toggle): A sticky sidebar displaying the 4 active source frameworks with their assigned color codes. It shows a live count of how many sections from each guideline were pulled to form the answer.
   - Center Pane (The Synthesis Engine): A data-dense, non-bubble, structured workspace. The prompt box sits cleanly at the bottom, resembling a "quiet, capable assistant".
   - Right Rail (The Evidence Vault): A contextual panel that automatically reveals the exact PDF snippet or text block of the cited section when a clinician clicks an in-text source citation.

---

## Visual Sourcing and Typography
- Clinicians must distinguish facts instantly. 
- Map the required visual color anchors into a clean, professional palette against a crisp white or neutral off-white background to ensure high readability
- In-Text Citation Pill Design
  - Never use vague footnotes. 
  - Use interactive, color-matched citation inline tags that embed directly into the text, formatted like this:
   ...initiate pharmacologic treatment at \(\ge \) 150/90 mmHg [JNC 8 § Rec 1]
   ...consider eGFR monitoring bi-annually [FDA § Warnings]

---

## Trust & Transparency

- In medicine, a "hallucinated" or uncertain answer can risk patient safety.
- **The Global Confidence Banner**
   - When retrieval confidence falls below your system's strict safety threshold, the entire answer window must change states to reflect the drop in confidence:
     1. UI Action: A persistent yellow top banner appears stating: "⚠️ Low Retrieval Confidence: Information could not be definitively cross-referenced across the active guidelines.
     2. "Granular Text Fogging: Sections of the response that generated the low confidence score should be accompanied by an inline alert pill [❓ Low Confidence Sync], signaling the physician to manually review the source text in the Right Rail.

## Some Optum Inspired UX-micro interactions

- The **"Copy for EHR Note"** Button: A single-click button that strips out the UI formatting and compiles the answer into a standardized clinical note format (e.g., SOAP note format) along with full text citations.
- **Hover-to-Peek**: Hovering over a citation icon yields a fast tool-tip displaying the raw quote from the source guideline without forcing the doctor to change windows or click away.
- **No Jargon in Tooltips**: Keep tooltips, system warnings, and UI microcopy clear and straightforward. If the AI fails to parse a section, state exactly why (e.g., "Error: Section missing from ADA 2024 index").

##  Sample UI Layout of an AI ResponseUser Query: 

> 72yo male, history of T2D, BP 152/94. Next steps?

**Clinical Guidance Engine** 

- **Blood Pressure ManagementThreshold Action**: For patients \(\ge \) 60 years old without underlying kidney disease, initiate pharmacologic therapy at a SBP \(\ge \) 150 mmHg or DBP \(\ge \) 90 mmHg 🟦 [JNC 8 § Recommendation 1].
- **Target Goal**: Titrate treatment to a target blood pressure of \(< 150/90\) mmHg 🟦 [JNC 8 § Recommendation 1].
- **Glycemic & Comorbidity ControlsFirst-Line Therapy**: Metformin remains foundational. Ensure renal function is evaluated prior to initiation 🟩 [ADA 2024 § Sec. 9].
- **Contraindication Check**: Do not initiate Metformin if eGFR falls below 30 mL/min/1.73m² 🟪 [FDA § Contraindications].

# Eval Question Set — ClinicalRAG (Claude 3.5 Sonnet generated)

---

## Questions — Doc 1: metformin_fda_label.pdf

| # | question | expected_answer_contains | source_doc | section | difficulty |
|---|----------|--------------------------|------------|---------|------------|
| 1 | What is the eGFR threshold below which metformin is absolutely contraindicated? | eGFR less than 30 mL/min/1.73 m2 | metformin_fda_label.pdf | contraindications | easy |
| 2 | The label says initiation of metformin is "not recommended" in a specific eGFR range — what is that range? | eGFR between 30 and 45 mL/min/1.73 m2 | metformin_fda_label.pdf | warnings_and_precautions | medium |
| 3 | A patient on metformin is scheduled for a CT scan with iodinated contrast and has an eGFR of 50 — what should happen to the metformin? | discontinue at the time of or prior to the procedure | metformin_fda_label.pdf | dosage_and_administration | medium |
| 4 | After stopping metformin for a contrast imaging procedure, when can it be restarted and what must be confirmed first? | re-evaluate eGFR 48 hours after the imaging procedure, restart if renal function is stable | metformin_fda_label.pdf | warnings_and_precautions | medium |
| 5 | How often should vitamin B12 levels specifically be monitored in patients taking metformin, and how often should hematological parameters be checked? | vitamin B12 at 2 to 3 year intervals, hematological parameters annually | metformin_fda_label.pdf | warnings_and_precautions | hard |
| 6 | Does metformin alone cause hypoglycemia under normal use conditions? | hypoglycemia does not occur with metformin alone under usual circumstances | metformin_fda_label.pdf | warnings_and_precautions | hard |
| 7 | What are the three absolute contraindications listed for metformin? | severe renal impairment eGFR below 30, hypersensitivity to metformin, acute or chronic metabolic acidosis including diabetic ketoacidosis | metformin_fda_label.pdf | contraindications | easy |
| 8 | The label identifies carbonic anhydrase inhibitors as a drug interaction concern for metformin — what specific risk do they increase and what action is recommended? | increase risk of lactic acidosis, consider more frequent monitoring | metformin_fda_label.pdf | drug_interactions | hard |
| 9 | What lab value threshold in mmol/L is used to characterize metformin-associated lactic acidosis in postmarketing cases? | elevated blood lactate concentrations greater than 5 mmol/L | metformin_fda_label.pdf | warnings_and_precautions | hard |
| 10 | For an elderly patient on metformin, does the label recommend titrating to the maximum dose? | titration to the maximum dose is generally not recommended in elderly debilitated or malnourished patients | metformin_fda_label.pdf | dosage_and_administration | medium |

---

## Questions — Doc 2: ada_standards_care_diabetes_section6.pdf

| # | question | expected_answer_contains | source_doc | section | difficulty |
|---|----------|--------------------------|------------|---------|------------|
| 1 | What is the A1C goal recommended for most nonpregnant adults with diabetes? | less than 7% or 53 mmol/mol | ada_standards_care_diabetes_section6.pdf | a1c_targets | easy |
| 2 | What TIR percentage corresponds approximately to an A1C of 7%? | TIR greater than 70% aligns with A1C of approximately 7% | ada_standards_care_diabetes_section6.pdf | cgm_targets | medium |
| 3 | What is the target for time below range on a CGM for most nonpregnant adults? | time below range less than 4% | ada_standards_care_diabetes_section6.pdf | cgm_targets | hard |
| 4 | What less stringent A1C threshold does the ADA recommend as acceptable for patients with limited life expectancy or where treatment harms outweigh benefits? | less than 8% or 64 mmol/mol | ada_standards_care_diabetes_section6.pdf | individualized_targets | medium |
| 5 | What is the A1C target for pregnant individuals with diabetes, and what relaxed target is allowed if that cannot be achieved without significant hypoglycemia? | less than 6%, can be relaxed to less than 7% if not achievable without significant hypoglycemia | ada_standards_care_diabetes_section6.pdf | individualized_targets | hard |
| 6 | What minimum CGM wear percentage is required over a 10 to 14 day period for TIR to be a valid assessment of glycemic status? | CGM wear of 70% or higher | ada_standards_care_diabetes_section6.pdf | cgm_targets | hard |
| 7 | Does the ADA 2023 section 6 consider severe hypoglycemia a marker for cardiovascular risk? | severe hypoglycemia is a potent marker of cardiovascular risk | ada_standards_care_diabetes_section6.pdf | hypoglycemia_risk | medium |
| 8 | What does GMI stand for and what is it used as an alternative or supplement to? | glucose management indicator, used as supplement to or alternative for A1C | ada_standards_care_diabetes_section6.pdf | glycemic_assessment_methods | medium |
| 9 | The ADA guidelines say a lower A1C than 7% may be appropriate in some patients — what two conditions must be met for this to be recommended? | can be achieved safely without significant hypoglycemia or other adverse effects of treatment | ada_standards_care_diabetes_section6.pdf | individualized_targets | hard |
| 10 | What is the very low threshold for time below range below 54 mg/dL that CGM targets aim to keep under? | less than 1% | ada_standards_care_diabetes_section6.pdf | cgm_targets | hard |

---

## Questions — Doc 3: ada_standards_care_diabetes_section9.pdf

| # | question | expected_answer_contains | source_doc | section | difficulty |
|---|----------|--------------------------|------------|---------|------------|
| 1 | For a T2D patient with established ASCVD, is GLP-1 RA or SGLT2 inhibitor recommended independent of A1C level or only after A1C target is missed? | recommended independent of A1C | ada_standards_care_diabetes_section9.pdf | cvd_ckd_drug_selection | medium |
| 2 | When a T2D patient with ASCVD is already at their A1C goal on other medications, does ADA section 9 still recommend switching to SGLT2i or GLP-1 RA? | yes, individuals already achieving glycemic goals may benefit from switching to reduce ASCVD HF CKD risk | ada_standards_care_diabetes_section9.pdf | cvd_ckd_drug_selection | hard |
| 3 | What does the ADA section 9 say should happen to metformin when insulin is being intensified — should it be stopped or continued? | metformin should be maintained unless adverse effects or contraindications are present | ada_standards_care_diabetes_section9.pdf | insulin_intensification | medium |
| 4 | When initial combination therapy should be considered according to ADA 2023 section 9 — what A1C threshold above an individual's goal triggers this? | A1C levels 1.5 to 2.0 percent above individualized goal | ada_standards_care_diabetes_section9.pdf | combination_therapy_rationale | hard |
| 5 | The ADA section 9 identifies a trade-off with stepwise therapy vs combination — what is the stated advantage of stepwise addition over initial combination? | provides clear assessment of positive and negative effects of new drugs and reduces potential side effects and expense | ada_standards_care_diabetes_section9.pdf | combination_therapy_rationale | hard |
| 6 | Which two drug classes should be continued and which two should be weaned when intensifying insulin therapy according to ADA 2023 section 9? | maintain SGLT2 inhibitors and GLP-1 RAs, wean sulfonylureas and DPP-4 inhibitors | ada_standards_care_diabetes_section9.pdf | insulin_intensification | hard |
| 7 | For a T2D patient with heart failure but no ASCVD, does ADA section 9 recommend SGLT2i or GLP-1 RA? | SGLT2 inhibitor and/or GLP-1 RA with demonstrated cardiovascular benefit | ada_standards_care_diabetes_section9.pdf | cvd_ckd_drug_selection | medium |
| 8 | Does the ADA 2023 section 9 recommend GLP-1 RAs as preferred over insulin for patients needing more glucose lowering than oral agents can provide? | GLP-1 RAs are preferred to insulin when possible | ada_standards_care_diabetes_section9.pdf | drug_class_profiles | medium |
| 9 | What does "independent of metformin use" mean in the ADA section 9 recommendation for SGLT2i/GLP-1 RA in ASCVD patients? | the recommendation applies whether or not the patient is already on metformin, with or without metformin | ada_standards_care_diabetes_section9.pdf | cvd_ckd_drug_selection | hard |
| 10 | Does ADA section 9 say medication regimen should be re-evaluated and at what time interval? | re-evaluated at regular intervals every 3 to 6 months | ada_standards_care_diabetes_section9.pdf | combination_therapy_rationale | easy |

---

## Questions — Doc 4: jnc8_guidelines_management_hypertension_original.pdf

| # | question | expected_answer_contains | source_doc | section | difficulty |
|---|----------|--------------------------|------------|---------|------------|
| 1 | At what blood pressure reading should pharmacologic treatment be initiated in a 65-year-old patient without diabetes or CKD, according to JNC 8? | systolic 150 mm Hg or higher or diastolic 90 mm Hg or higher | jnc8_guidelines_management_hypertension_original.pdf | recommendation_1 | easy |
| 2 | A 65-year-old patient with no DM or CKD is on antihypertensive therapy — what is their BP target according to JNC 8? | less than 150/90 mm Hg | jnc8_guidelines_management_hypertension_original.pdf | recommendation_1 | easy |
| 3 | A 45-year-old patient with no comorbidities has BP of 145/88 — does JNC 8 recommend initiating pharmacologic treatment? | yes, initiation threshold for adults younger than 60 is SBP 140 or DBP 90 | jnc8_guidelines_management_hypertension_original.pdf | recommendation_2 | medium |
| 4 | For a patient with CKD aged 72, what is the blood pressure target according to JNC 8 — same as general elderly or different? | target less than 140/90, not the less stringent less than 150/90 used for general elderly without CKD | jnc8_guidelines_management_hypertension_original.pdf | recommendation_3 | hard |
| 5 | JNC 8 explicitly says there is no evidence for a lower BP target in CKD patients — does it still recommend less than 140/90 for them despite lack of evidence for benefit below that? | yes, target is less than 140/90 for CKD patients regardless of age | jnc8_guidelines_management_hypertension_original.pdf | recommendation_3 | hard |
| 6 | A Black patient with hypertension and no CKD presents for first-line treatment — which drug classes does JNC 8 recommend and which does it explicitly exclude as less effective monotherapy? | thiazide-type diuretics or calcium channel blockers; ACE inhibitors and ARBs are less effective as monotherapy in Black patients | jnc8_guidelines_management_hypertension_original.pdf | pharmacologic_treatment_black | medium |
| 7 | JNC 8 prohibits combining two specific drug classes — which combination is explicitly not recommended? | do not combine ACE inhibitor with ARB | jnc8_guidelines_management_hypertension_original.pdf | acei_arb_combination_prohibition | easy |
| 8 | If a patient's BP target is not reached after starting antihypertensive therapy, what is the JNC 8 recommended time window and action? | if target not reached within one month, increase dose of initial medication or add a second medication | jnc8_guidelines_management_hypertension_original.pdf | titration_protocol | medium |
| 9 | A Black patient with CKD and hypertension is being treated — does the race-based first-line recommendation (thiazide/CCB only) still apply, or does CKD change the drug selection? | CKD overrides race-based recommendation; ACEI or ARB required for CKD patients regardless of race | jnc8_guidelines_management_hypertension_original.pdf | ckd_treatment | hard |
| 10 | JNC 8 lists exactly four drug classes as acceptable for first-line and later-line treatment — what are they? | thiazide-type diuretics, calcium channel blockers, ACE inhibitors, angiotensin receptor blockers | jnc8_guidelines_management_hypertension_original.pdf | pharmacologic_treatment_nonblack | easy |

---

## Questions — System should say "insufficient context" or "information not available"

These questions cannot be answered from the four documents. The system should return a low confidence score and a disclaimer, not a fabricated answer.

| # | question | why this fails | expected response | expected confidence score |
|---|----------|----------------|-------------------|--------------------------|
| 1 | What is the current market price of semaglutide (Ozempic)? | No pricing data exists in any of the four clinical documents | "This information is not available in the clinical documents provided. Please consult a formulary or pharmacy pricing source." | < 0.3 |
| 2 | Can metformin be used to treat polycystic ovary syndrome (PCOS)? | PCOS is not mentioned in the metformin FDA label indexed here — it is an off-label use not covered in the prescribing information | Low confidence answer; disclaimer that off-label uses are not covered in the indexed FDA label | < 0.5 |
| 3 | What A1C threshold triggers insulin initiation in a newly diagnosed T2D patient with no comorbidities, according to ADA 2023? | ADA section 9 addresses when to add insulin to existing therapy; it does not define a numeric A1C initiation threshold for new diagnosis in the indexed sections | "The indexed sections of the ADA guidelines do not specify a numeric A1C threshold for insulin initiation at diagnosis. Please consult the full guidelines." | < 0.55 |
| 4 | Which specific SGLT2 inhibitor brand has the most evidence for cardiovascular benefit in heart failure patients? | The ADA section 9 references SGLT2 inhibitors as a class with cardiovascular benefit and mentions demonstrated CVD benefit but the specific brand-level evidence comparison is in Table 9.2 which is not available in the indexed text | "The specific comparative brand-level evidence table is not available in the indexed document sections. The guidelines recommend SGLT2 inhibitors with demonstrated cardiovascular benefit — consult Table 9.2 of the full ADA guidelines." | < 0.5 |
| 5 | What is the recommended sodium intake per day for a hypertension patient according to JNC 8? | JNC 8 mentions lifestyle interventions including sodium reduction but the specific numeric gram recommendation (2.4g/day) is in the lifestyle section which may not be in the indexed chunks | Low confidence; if retrieved: "reduce sodium intake" without the specific number, system should flag the specific number as uncertain | < 0.6 |
| 6 | Is metformin safe to use during pregnancy? | The metformin FDA label addresses use in specific populations including pregnancy, but the question requires a nuanced safety classification that the label approaches cautiously — the exact pregnancy category and risk language is in a subsection that may not be retrieved cleanly | Low confidence; disclaimer to consult the full prescribing information and obstetric guidance | < 0.55 |
| 7 | What is the recommended blood pressure target for a 62-year-old diabetic patient who also has stage 4 CKD, according to JNC 8? | This requires applying both the diabetes recommendation (< 140/90) AND the CKD recommendation (< 140/90) simultaneously — both give the same answer here, but the system may retrieve one recommendation without the other and produce an incomplete answer | System should retrieve both recommendations and confirm they align; confidence depends on whether both chunks are retrieved | < 0.65 |
| 8 | How does ADA 2023 define "high ASCVD risk" — what specific clinical criteria qualify a patient? | The specific definition of "indicators of high ASCVD risk" is referenced in ADA section 9 but the detailed clinical criteria (age, coronary stenosis threshold, LVH, etc.) are defined in Section 10 which is not in the indexed corpus | "The ADA 2023 section 9 references indicators of high ASCVD risk but the specific criteria definition is in Section 10, which is not available in the indexed documents." | < 0.45 |
| 9 | What is the exact half-life of metformin in patients with normal renal function? | Pharmacokinetic details like half-life values are in the Clinical Pharmacology section (Section 12) of the FDA label, which is excluded from indexing as lower clinical priority content | "The clinical pharmacology section containing half-life data is not included in the indexed portions of the FDA label." | < 0.35 |
| 10 | Does JNC 8 recommend beta-blockers as a first-line antihypertensive option? | Beta-blockers are explicitly not included in JNC 8's four first-line drug classes — the system should answer this correctly as a "no" with citation, but may confuse it with earlier JNC 7 guidance if confidence is low | "JNC 8 does not include beta-blockers among the four recommended first-line drug classes (thiazide diuretics, CCBs, ACEIs, ARBs)." | > 0.7 — this one should actually answer correctly |
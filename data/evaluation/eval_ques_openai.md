# Eval Question Set — ClinicalRAG (ChatGPT generated)

> Questions generated after analyzing:
>
> * FDA Metformin Label
> * ADA Standards of Care Sections 6 & 9
> * JNC 8 Hypertension Guidelines
>
> Focus Areas:
>
> * preprocessing edge cases
> * chunking failures
> * table understanding
> * hallucination detection
> * cross-document reasoning
> * abbreviation normalization
> * retrieval robustness
> * safety-critical information retrieval

---

# Questions — Doc 1: metformin_fda_label.pdf

| #  | question                                                                                                  | expected_answer_contains                                                     | source_doc              | section                   | difficulty |
| -- | --------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------- | ------------------------- | ---------- |
| 1  | What is the maximum recommended daily dose for metformin extended-release tablets?                        | 2000 mg/day                                                                  | metformin_fda_label.pdf | dosage_and_administration | easy       |
| 2  | At what eGFR value is metformin contraindicated?                                                          | eGFR below 30 mL/min/1.73m²                                                  | metformin_fda_label.pdf | contraindications         | easy       |
| 3  | What recommendation is given for starting metformin in elderly patients?                                  | start at lower dosage range and monitor renal function frequently            | metformin_fda_label.pdf | geriatric_use             | medium     |
| 4  | What should happen to metformin therapy during iodinated contrast imaging procedures?                     | temporarily discontinue metformin and reassess renal function after 48 hours | metformin_fda_label.pdf | warnings_and_precautions  | medium     |
| 5  | Which boxed warning appears repeatedly throughout the document?                                           | lactic acidosis                                                              | metformin_fda_label.pdf | boxed_warning             | easy       |
| 6  | What issue can happen if the highlights section is indexed together with full prescribing information?    | duplicate retrieval wasting context slots                                    | metformin_fda_label.pdf | preprocessing_notes       | hard       |
| 7  | Which adverse reaction appears with higher frequency than placebo in the clinical trials table?           | diarrhea                                                                     | metformin_fda_label.pdf | adverse_reactions         | medium     |
| 8  | Why is the table of contents removed during preprocessing?                                                | contains keywords that create retrieval noise                                | metformin_fda_label.pdf | preprocessing_notes       | hard       |
| 9  | What alcohol-related risk is mentioned in the drug interactions section?                                  | alcohol increases risk of lactic acidosis                                    | metformin_fda_label.pdf | drug_interactions         | medium     |
| 10 | What problem occurs if table rows like “Diarrhea 10% 3%” are chunked directly?                            | values lose meaning without headers                                          | metformin_fda_label.pdf | table_processing          | hard       |
| 11 | Which condition besides renal impairment is listed as a contraindication?                                 | metabolic acidosis including diabetic ketoacidosis                           | metformin_fda_label.pdf | contraindications         | medium     |
| 12 | Why are inline references like “[see section 5.1]” removed before embedding?                              | semantic embedding pollution                                                 | metformin_fda_label.pdf | preprocessing_notes       | hard       |
| 13 | What preprocessing normalization is applied to “Vitamin B 12”?                                            | converted to Vitamin B12                                                     | metformin_fda_label.pdf | normalization             | hard       |
| 14 | What retrieval issue can happen if contraindications and dosage recommendations appear in the same chunk? | context contamination between safe and unsafe usage guidance                 | metformin_fda_label.pdf | chunking_notes            | hard       |
| 15 | Which metadata fields should be stored separately instead of inside embeddings?                           | manufacturer name, approval date, document identifiers                       | metformin_fda_label.pdf | metadata_processing       | hard       |

---

# Questions — Doc 2: ada_standards_care_diabetes_6.pdf

| #  | question                                                                               | expected_answer_contains                                     | source_doc                        | section                     | difficulty |
| -- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------ | --------------------------------- | --------------------------- | ---------- |
| 1  | What A1C target is recommended for most nonpregnant adults?                            | A1C below 7%                                                 | ada_standards_care_diabetes_6.pdf | a1c_targets                 | easy       |
| 2  | What CGM metric roughly corresponds to A1C below 7%?                                   | time in range greater than 70%                               | ada_standards_care_diabetes_6.pdf | cgm_targets                 | medium     |
| 3  | Why are evidence grades like “(A)” removed from chunk text?                            | they add embedding noise                                     | ada_standards_care_diabetes_6.pdf | preprocessing_notes         | hard       |
| 4  | Which patient groups may need less stringent A1C goals?                                | elderly patients and patients with comorbidities             | ada_standards_care_diabetes_6.pdf | individualized_targets      | medium     |
| 5  | What preprocessing issue is caused by inline citation numbers like “(24–29)”?          | irrelevant semantic tokens inside embeddings                 | ada_standards_care_diabetes_6.pdf | preprocessing_notes         | hard       |
| 6  | Which monitoring method besides A1C is discussed heavily in the document?              | continuous glucose monitoring                                | ada_standards_care_diabetes_6.pdf | glycemic_assessment_methods | easy       |
| 7  | What does TIR stand for?                                                               | time in range                                                | ada_standards_care_diabetes_6.pdf | abbreviations               | easy       |
| 8  | Why are figure references like “Figure 6.1” removed from running text?                 | figures are unavailable in extracted chunk text              | ada_standards_care_diabetes_6.pdf | preprocessing_notes         | medium     |
| 9  | What risk is associated with intensive glycemic control?                               | severe hypoglycemia                                          | ada_standards_care_diabetes_6.pdf | hypoglycemia_risk           | medium     |
| 10 | What normalization issue exists between A1C, HbA1c, and HbA1C?                         | same metric represented differently across documents         | ada_standards_care_diabetes_6.pdf | normalization               | hard       |
| 11 | Why should recommendation IDs like “6.3a” be stored as metadata instead of chunk text? | they are not semantically useful for retrieval               | ada_standards_care_diabetes_6.pdf | preprocessing_notes         | hard       |
| 12 | What retrieval issue happens if author lists are not removed from the document?        | generic diabetes queries may retrieve author metadata        | ada_standards_care_diabetes_6.pdf | preprocessing_notes         | hard       |
| 13 | What percentage of time below range is recommended to reduce hypoglycemia risk?        | less than 4%                                                 | ada_standards_care_diabetes_6.pdf | cgm_targets                 | medium     |
| 14 | What does GMI represent in CGM monitoring?                                             | glucose management indicator                                 | ada_standards_care_diabetes_6.pdf | abbreviations               | medium     |
| 15 | Why can citation-heavy chunks reduce retrieval quality?                                | embeddings prioritize citation patterns over medical meaning | ada_standards_care_diabetes_6.pdf | preprocessing_notes         | hard       |

---

# Questions — Doc 3: ada_standards_care_diabetes_9.pdf

| #  | question                                                                                   | expected_answer_contains                             | source_doc                        | section                 | difficulty |
| -- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------- | --------------------------------- | ----------------------- | ---------- |
| 1  | Which medication is described as established first-line therapy for type 2 diabetes?       | metformin                                            | ada_standards_care_diabetes_9.pdf | first_line_treatment    | easy       |
| 2  | Which drug class is preferred for CKD or heart failure patients?                           | SGLT2 inhibitors                                     | ada_standards_care_diabetes_9.pdf | cvd_ckd_drug_selection  | medium     |
| 3  | Which therapy is preferred for patients with established cardiovascular disease?           | GLP-1 receptor agonists                              | ada_standards_care_diabetes_9.pdf | cvd_ckd_drug_selection  | medium     |
| 4  | What insulin initiation dose range is mentioned?                                           | 0.4–1.0 units/kg/day                                 | ada_standards_care_diabetes_9.pdf | insulin_initiation      | medium     |
| 5  | What retrieval issue can happen if multiple therapy strategies are chunked together?       | context contamination between treatment pathways     | ada_standards_care_diabetes_9.pdf | chunking_notes          | hard       |
| 6  | What preprocessing issue exists with “Adapted from...” attribution lines?                  | they appear as semantic noise inside chunks          | ada_standards_care_diabetes_9.pdf | preprocessing_notes     | medium     |
| 7  | Which abbreviations appear repeatedly in the document?                                     | GLP-1 RA, SGLT2i, CKD, CVD                           | ada_standards_care_diabetes_9.pdf | abbreviations           | easy       |
| 8  | Why should abbreviation expansion happen before embedding?                                 | retrieval may fail on synonym queries otherwise      | ada_standards_care_diabetes_9.pdf | normalization           | hard       |
| 9  | Which medications may be continued during insulin intensification?                         | metformin, SGLT2 inhibitors, GLP-1 receptor agonists | ada_standards_care_diabetes_9.pdf | insulin_intensification | hard       |
| 10 | Which medication class may be reduced during insulin intensification?                      | sulfonylureas                                        | ada_standards_care_diabetes_9.pdf | insulin_intensification | medium     |
| 11 | What document structure issue can cause chunk overlap redundancy?                          | repeated recommendation summaries                    | ada_standards_care_diabetes_9.pdf | chunking_notes          | hard       |
| 12 | Why are recommendation evidence grades stored as metadata?                                 | useful for filtering but noisy for embeddings        | ada_standards_care_diabetes_9.pdf | preprocessing_notes     | hard       |
| 13 | What lifestyle recommendations are paired with metformin therapy?                          | diet and exercise                                    | ada_standards_care_diabetes_9.pdf | first_line_treatment    | easy       |
| 14 | During which conditions may insulin requirements increase?                                 | puberty, pregnancy, illness                          | ada_standards_care_diabetes_9.pdf | insulin_initiation      | medium     |
| 15 | What retrieval issue occurs if SGLT2i and GLP-1 recommendations are merged into one chunk? | model may confuse cardiovascular vs CKD guidance     | ada_standards_care_diabetes_9.pdf | chunking_notes          | hard       |

---

# Questions — Doc 4: jnc8_guidelines_management_hypertension_original.pdf

| #  | question                                                                                     | expected_answer_contains                             | source_doc                                           | section                          | difficulty |
| -- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- | -------------------------------- | ---------- |
| 1  | What BP target is recommended for adults aged 60 years or older?                             | below 150/90                                         | jnc8_guidelines_management_hypertension_original.pdf | recommendation_1                 | easy       |
| 2  | What BP target is recommended for adults younger than 60?                                    | below 140/90                                         | jnc8_guidelines_management_hypertension_original.pdf | recommendation_2                 | easy       |
| 3  | Which medication combination should not be used together?                                    | ACE inhibitor with ARB                               | jnc8_guidelines_management_hypertension_original.pdf | acei_arb_combination_prohibition | medium     |
| 4  | Why is one-recommendation-per-chunk used for this document?                                  | avoid mixing population-specific BP targets          | jnc8_guidelines_management_hypertension_original.pdf | chunking_notes                   | hard       |
| 5  | Which medication classes are recommended first-line for non-Black patients?                  | thiazide diuretic, ACEI, ARB, CCB                    | jnc8_guidelines_management_hypertension_original.pdf | pharmacologic_treatment_nonblack | medium     |
| 6  | Which therapies are preferred first-line for Black patients?                                 | thiazide diuretics or calcium channel blockers       | jnc8_guidelines_management_hypertension_original.pdf | pharmacologic_treatment_black    | medium     |
| 7  | What should happen if BP target is not achieved within one month?                            | increase dose or add second medication               | jnc8_guidelines_management_hypertension_original.pdf | titration_protocol               | easy       |
| 8  | What preprocessing issue exists with the “Key Points for Practice” section?                  | duplicates recommendation content                    | jnc8_guidelines_management_hypertension_original.pdf | preprocessing_notes              | medium     |
| 9  | Why are negative instructions preserved carefully during cleaning?                           | clinically important prohibitions may be lost        | jnc8_guidelines_management_hypertension_original.pdf | safety_processing                | hard       |
| 10 | Which abbreviations appear heavily in recommendation sections?                               | ACEI, ARB, CCB, SBP, DBP                             | jnc8_guidelines_management_hypertension_original.pdf | abbreviations                    | easy       |
| 11 | Why can chunking multiple recommendations together cause retrieval failures?                 | thresholds for different patient groups become mixed | jnc8_guidelines_management_hypertension_original.pdf | chunking_notes                   | hard       |
| 12 | What metadata should be removed from chunk text?                                             | publication and endorsement information              | jnc8_guidelines_management_hypertension_original.pdf | metadata_processing              | medium     |
| 13 | Which patient group specifically requires ACEI or ARB for renal protection?                  | CKD patients                                         | jnc8_guidelines_management_hypertension_original.pdf | ckd_treatment                    | medium     |
| 14 | What retrieval risk exists if BP thresholds and treatment targets appear in separate chunks? | incomplete hypertension recommendations              | jnc8_guidelines_management_hypertension_original.pdf | chunking_notes                   | hard       |
| 15 | Why are trial acronym expansions useful during preprocessing?                                | improves semantic retrieval quality                  | jnc8_guidelines_management_hypertension_original.pdf | normalization                    | hard       |

---

# Questions — Cross Document Understanding

| # | question                                                                        | expected_answer_contains                              | source_doc      | section                          | difficulty |
| - | ------------------------------------------------------------------------------- | ----------------------------------------------------- | --------------- | -------------------------------- | ---------- |
| 1 | What guidance exists for a CKD patient taking metformin with eGFR below 30?     | metformin contraindicated in severe renal impairment  | metformin + ADA | contraindications + CKD guidance | hard       |
| 2 | Which documents discuss CKD-related treatment recommendations?                  | metformin label, ADA guidelines, JNC8                 | all_docs        | cross_document                   | medium     |
| 3 | Which document contains cardiovascular drug selection guidance?                 | ADA section 9 and JNC8                                | ada_9 + jnc8    | cross_document                   | medium     |
| 4 | Which document discusses renal protection using ACEI or ARB?                    | JNC8 guideline                                        | jnc8            | ckd_treatment                    | medium     |
| 5 | Which document mentions SGLT2 inhibitors for CKD patients?                      | ADA standards section 9                               | ada_9           | cvd_ckd_drug_selection           | medium     |
| 6 | Which abbreviation appears across multiple documents with the same meaning?     | CKD                                                   | all_docs        | normalization                    | easy       |
| 7 | Which metric appears as A1C, HbA1c, and HbA1C across documents?                 | glycated hemoglobin                                   | metformin + ADA | normalization                    | hard       |
| 8 | What retrieval issue occurs if cross-document abbreviations are not normalized? | semantically related chunks may not retrieve together | all_docs        | normalization                    | hard       |

---

# Questions — Chunking Evaluation

| # | question                                                                              | expected_answer_contains                        | source_doc              | section             | difficulty |
| - | ------------------------------------------------------------------------------------- | ----------------------------------------------- | ----------------------- | ------------------- | ---------- |
| 1 | What failure can happen if contraindications and dosage instructions share one chunk? | unsafe recommendation mixing                    | metformin_fda_label.pdf | chunking_notes      | hard       |
| 2 | Why are JNC8 recommendations chunked individually?                                    | different patient populations and BP thresholds | jnc8                    | chunking_notes      | hard       |
| 3 | What issue happens if overlap is too large across chunks?                             | duplicate retrieval in top-k results            | all_docs                | chunking_notes      | medium     |
| 4 | What issue happens if chunks are too small?                                           | incomplete clinical context                     | all_docs                | chunking_notes      | medium     |
| 5 | Why should tables be converted into prose before chunking?                            | table rows lose semantic meaning                | metformin_fda_label.pdf | table_processing    | hard       |
| 6 | What retrieval issue can happen when figure captions are chunked alone?               | orphaned context retrieval                      | ADA docs                | preprocessing_notes | hard       |

---

# Questions — Normalization Testing

| # | question                                                    | expected_answer_contains                | source_doc              | section             | difficulty |
| - | ----------------------------------------------------------- | --------------------------------------- | ----------------------- | ------------------- | ---------- |
| 1 | What normalization is applied to HbA1c, HbA1C, and A1C?     | normalized to A1C (glycated hemoglobin) | ADA + metformin         | normalization       | hard       |
| 2 | Why is “Vitamin B 12” normalized to “Vitamin B12”?          | improve semantic retrieval consistency  | metformin_fda_label.pdf | normalization       | medium     |
| 3 | Why are ACEI and ACE inhibitor expanded together?           | retrieval should work for both forms    | jnc8                    | normalization       | medium     |
| 4 | What retrieval issue occurs without abbreviation expansion? | synonym queries fail to retrieve chunks | all_docs                | normalization       | hard       |
| 5 | Why are units like mmol/L and mg/dL preserved exactly?      | units contain clinical meaning          | all_docs                | preprocessing_notes | medium     |

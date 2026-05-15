# preprocessing_specs_dev.md

- for custom document preprocessing
- this file contains all my observations/rules after reading the actual source documments - not hypothetical

## Document 1 - metformin_fda_label.pdf

### Observations

1. same header on each page - This label may not be the latest approved by FDA.
For current labeling information, please visit https://www.fda.gov/drugsatfda
2. footer contain reference id and page number e.g. 6 in bottom center and Reference ID: 4079189 at bottom left
3. lot of Acronyms present like GLUCOPHAGE, AUC, etc
4. references present like (see precautions, see table 1)
5. words with Subscript and superscript present like Cmax, Tmax c
6. Not very big paragraphs
7. on first page - there is duplicate heading - GLUCOPHAGE®
(metformin hydrochloride) Tablets and GLUCOPHAGE® XR
(metformin hydrochloride) Extended-Release Tablets
8. Short forms used for representing words- (we need to record the the actual word and its short form at its first occurence)
9. table lose context without its header - one approach coming in my mind is convert table into readable sentences
10. Vitamin B 12 or B12 or vitamin B12 all should be treat as same - normalize first such words

## Document 2 - ada_standards_care_diabetes_6

### Observations

1. challenging document
2. repeating header - with bit different formats
   - diabetesjournals.org/care                          Glycemic Targets S99
   - S98 Glycemic         Targets Diabetes Care Volume 46, Supplement 1, January 2023
   - Diabetes Care Volume 46, Supplement 1, January 2023             S97
3. page 1 is very cluttered and not very informative (i think we can leave it but not sure as i am not from medical background)
4. no footer
5. multi column paragraphs format - 3 columns
6. Various images, graphs, daigrams are there
7. there is evidence grading - A,B,C,D,E like in "Insulin-treated patients with hypoglycemia
unawareness, one
level 3 hypoglycemic event, or a
pattern of unexplained level 2
hypoglycemia should be advised
to raise their glycemic targets
to strictly avoid hypoglycemia
for at least several weeks in order
to partially reverse hypoglycemia
unawareness and reduce
risk of future episodes. A" we can have this grade with metadata
8. references like "in Fig. 6.2" are present - need to remove them
9. not sure but maybe these are also reference - (70)
10. Huge list of references at the last (Starting with - References
Deshmukh H, Wilmot EG, Gregory R, et al.
Effect of flash glucose monitoring on glycemic
control, hypoglycemia, diabetes-related distress,
and resource utilization in the Association of
British Clinical Diabetologists (ABCD) nationwide
audit. Diabetes Care 2020;43:2153–2160
) - we can remove it
11. Short forms used like continuous glucose monitoring
(CGM) - Expand abbreviations on first occurrence.



## Document 3 - ada_standards_care_diabetes_9

### Observations

- same as Document 2


## Document 4 - jnc8_guidelines_management_hypertension

### Observations 

- not the complete document which i want

## Document 4 (original) - jnc8_guidelines_manage_hypertension_original.pdf

### Observations

- 2 column page format
- lots of abbreviation like ACEI angiotensin-converting enzyme
inhibitor
ARB angiotensin receptor blocker
BP blood pressure
CCB calcium channel blocker
CKD chronic kidney disease
CVD cardiovascular disease
ESRD end-stage renal disease
GFR glomerular filtration rate
HF heart failure
Expand & Normalize abbreviations on first occurrence.
- need to remove header
- need to remover footer
- footer has three lines to remove from bottom, first is like - 508 JAMA February 5, 2014 Volume 311, Number 5 jama.com, second is - Copyright © 2014 American Medical Association., third is - Downloaded from jamanetwork.com by Anshika Goel on 05/14/2026
- page 1 has summary or key pints kind of thing - these are not part of guidelines, can remove them
- need to maintain the order of the content - as the content is not in order in the document
- having references like (in Table 1) or (70) like - need to remove
- Normalize different formats of same word
- there is table three for grade system for each recommentation, each recommendation has grades and evidence type, we need to keep it as metadata
e.g. Recommendation 1
In the general population aged 60 years or older, initiate pharmacologic
treatment to lowerBPat systolic blood pressure (SBP) of 150
mmHg or higher or diastolic blood pressure (DBP) of 90mmHg or
higher and treat to a goal SBP lower than 150mmHg and goal DBP
lower than 90mmHg.
Strong Recommendation – Grade A
- i think in this we should have each recommentation as a chunk, along with its grade and evidence type (metadata)
-  there are some negative instructions too - very improtant to keep them e.g. (Avoid tight BP control in patients with CKD and.
CVD) and i think we can flag them too (safety concerns)
- at 512 page, there is a full flow chart daigram - it feels important, but not sure how to extract it, ask AI if it can extract and make a flow chart text or simply convert it into text format. If not then we can skip it. or some way out.
- there is a list of ARTICLE INFORMATION and REFERENCES at the last - we can remove them, but need to confirm that they are not imporant.

## Document 5 - nutrients-11-00766.pdf (Reversing Type 2 Diabetes: A Narrative Review of the Evidence)

- lets leave this document for now, as it is not required for prototype.


## General Notes from my side

- we can remove hyphenated words which are broken into two lines
- normalize words cross the documents (same medical term , different formats)
- while normalizing do not change the meaning or context of the word
- do not change the abbreviation form while normalizing unless it is required for better search, but we need to expand the abbreviation at least once in the document
- medical information should preioritize the dose usage, negative instruction like dont use this, side effects, boxed warning - we need to flag them and make sure to give in retrieval.

## Metadata to keep - 
- page number
- document id
- document name
- section name (like Recommendation 1 in JNC)
- section number
- subsection name
- subsection number
- grade (like Grade A in JNC)
- evidence type (like Evidence A in JNC)
- table number (like Table 1 in ADA)
- figure number (like Figure 1 in ADA)
- references (like reference 1 in ADA)


## how to handle tables
- first extract with pdfplumber and convert table into readable sentences with comma separated values

## how to handle graphs and figures
- need to ask AI about this as 

## how to handle headers and footers
- need to remove them

## how to handle references
- need to remove them, keep in metadata only if needed


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


import sys, logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, 'src')
sys.path.insert(0, 'experiments/chunking')

def safe_print(*args):
    text = ' '.join(str(a) for a in args)
    sys.stdout.buffer.write((text + '\n').encode('utf-8', errors='replace'))
    sys.stdout.buffer.flush()
from strategies import boundary_aware_chunks, fixed_size_chunks, sentence_window_chunks

safe_print("=== boundary_aware 512 ===")
chunks = boundary_aware_chunks(
    doc_id='ada_standards_care_diabetes_6',
    pdf_path='data/raw/ada_standards_care_diabetes_6.pdf',
    token_size=512
)
safe_print(f'chunks: {len(chunks)}')
if chunks:
    c = chunks[0]
    safe_print('text[:120]:', c['text'][:120])
    for k in ['strategy','token_size','section_name','evidence_grade','safety_flag']:
        safe_print(f'  {k}: {c["metadata"].get(k)}')

safe_print()
safe_print("=== fixed_size 512 ===")
chunks2 = fixed_size_chunks(
    doc_id='ada_standards_care_diabetes_6',
    pdf_path='data/raw/ada_standards_care_diabetes_6.pdf',
    token_size=512
)
safe_print(f'chunks: {len(chunks2)}')

safe_print()
safe_print("=== sentence_window 512 ===")
chunks3 = sentence_window_chunks(
    doc_id='ada_standards_care_diabetes_6',
    pdf_path='data/raw/ada_standards_care_diabetes_6.pdf',
    token_size=512
)
safe_print(f'chunks: {len(chunks3)}')
safe_print("SMOKE TEST PASSED")

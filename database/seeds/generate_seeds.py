import re
import uuid
import json
import hashlib
import openpyxl

def parse_markdown_table_lines(lines):
    rows = []
    headers = []
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if not cells:
            continue
        if all(c.startswith('-') or c == '' for c in cells):
            # separator line
            continue
        if not headers:
            headers = cells
        else:
            rows.append(dict(zip(headers, cells)))
    return rows

def clean_sql_val(val):
    if val is None:
        return 'NULL'
    escaped = val.replace("'", "''")
    return f"'{escaped}'"

def main():
    # 1. Load embeddings.jsonl mapped by (document_id, content_sha256)
    embeddings = {}
    with open('/home/elior/Documents/aabw_tascotrack_p1/embeddings.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                # Resolve doc_id from document_version_id
                doc_id = data['document_version_id'].split('-')[0]
                embeddings[(doc_id, data['content_sha256'])] = data
    print(f"Loaded {len(embeddings)} unique embeddings from embeddings.jsonl")

    # 2. Read Documents from Excel
    wb = openpyxl.load_workbook('/home/elior/Documents/aabw_tascotrack_p1/ai_workspace_dataset_vietnamese_participants.xlsm', read_only=True)
    ws = wb['Documents']
    excel_docs = {}
    for row in ws.iter_rows(values_only=True):
        if row and len(row) > 4 and row[0] and str(row[0]).startswith('DOC'):
            excel_docs[row[0]] = row[4]
    print(f"Loaded {len(excel_docs)} documents from Excel")

    # 3. Read data.md for other tables
    with open('/home/elior/Documents/aabw_tascotrack_p1/data.md', 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    sections = {}
    current_section = None
    section_lines = []
    
    for line in lines:
        header_match = re.match(r'^##\s+(\d+\.\s+\w+)', line)
        if header_match:
            if current_section:
                sections[current_section] = section_lines
            current_section = header_match.group(1).strip()
            section_lines = []
        else:
            if current_section:
                section_lines.append(line)
    if current_section:
        sections[current_section] = section_lines

    dept_lines = [v for k, v in sections.items() if 'Departments' in k][0]
    dept_rows = parse_markdown_table_lines(dept_lines)

    role_lines = [v for k, v in sections.items() if 'Roles' in k][0]
    role_rows = parse_markdown_table_lines(role_lines)

    perm_lines = [v for k, v in sections.items() if 'Permissions' in k][0]
    perm_rows = parse_markdown_table_lines(perm_lines)

    user_rows = parse_markdown_table_lines([v for k, v in sections.items() if 'Users' in k][0])
    meta_rows = parse_markdown_table_lines([v for k, v in sections.items() if 'Document_Metadata' in k][0])
    eval_rows = parse_markdown_table_lines([v for k, v in sections.items() if 'Public_Evaluation' in k or 'Public Evaluation' in k][0])

    dept_name_to_id = {
        'Company': 'COMP',
        'Human Resources': 'HR',
        'Finance': 'FIN',
        'Product': 'PROD',
        'Engineering': 'ENG',
        'Operations': 'OPS',
        'Legal & Compliance': 'LEGAL',
        'Executive Office': 'EXEC'
    }

    sql_statements = []
    sql_statements.append("BEGIN;")
    sql_statements.append("TRUNCATE TABLE public_evaluation_cases CASCADE;")
    sql_statements.append("TRUNCATE TABLE chunks CASCADE;")
    sql_statements.append("TRUNCATE TABLE documents CASCADE;")
    sql_statements.append("TRUNCATE TABLE users CASCADE;")
    sql_statements.append("TRUNCATE TABLE permissions CASCADE;")
    sql_statements.append("TRUNCATE TABLE roles CASCADE;")
    sql_statements.append("TRUNCATE TABLE departments CASCADE;")

    # Seeding departments, roles, permissions, users
    sql_statements.append("\n-- Seeding departments")
    for row in dept_rows:
        sql_statements.append(
            f"INSERT INTO departments (id, department_id, department_en, department_vi, knowledge_space) VALUES ("
            f"gen_random_uuid(), {clean_sql_val(row['department_id'])}, {clean_sql_val(row['department_en'])}, "
            f"{clean_sql_val(row['department_vi'])}, {clean_sql_val(row['knowledge_space'])});"
        )

    sql_statements.append("\n-- Seeding roles")
    for row in role_rows:
        sql_statements.append(
            f"INSERT INTO roles (id, role_en, role_vi, company_knowledge, department_knowledge, executive_knowledge) VALUES ("
            f"gen_random_uuid(), {clean_sql_val(row['role_en'])}, {clean_sql_val(row['role_vi'])}, "
            f"{clean_sql_val(row['company_knowledge'])}, {clean_sql_val(row['department_knowledge'])}, "
            f"{clean_sql_val(row['executive_knowledge'])});"
        )

    sql_statements.append("\n-- Seeding permissions")
    for row in perm_rows:
        sql_statements.append(
            f"INSERT INTO permissions (id, classification, employee, manager, director, executive, rule_description_vi) VALUES ("
            f"gen_random_uuid(), {clean_sql_val(row['classification'])}, {clean_sql_val(row['employee'])}, "
            f"{clean_sql_val(row['manager'])}, {clean_sql_val(row['director'])}, "
            f"{clean_sql_val(row['executive'])}, {clean_sql_val(row['rule_description_vi'])});"
        )

    sql_statements.append("\n-- Seeding users")
    for row in user_rows:
        raw_dept = row['department']
        dept_id = dept_name_to_id.get(raw_dept, raw_dept)
        sql_statements.append(
            f"INSERT INTO users (id, user_id, full_name, department_id, role_en, email, status) VALUES ("
            f"gen_random_uuid(), {clean_sql_val(row['user_id'])}, {clean_sql_val(row['full_name'])}, "
            f"'{dept_id}', {clean_sql_val(row['role'])}, "
            f"{clean_sql_val(row['email'])}, {clean_sql_val(row['status'])});"
        )

    # Insert Documents and Chunks with embeddings
    sql_statements.append("\n-- Seeding documents & chunks")
    
    matched_chunks_count = 0
    total_chunks_count = 0
    
    for row in meta_rows:
        doc_id = row['document_id']
        u = str(uuid.uuid4())
        
        raw_dept = row['department']
        dept_id = dept_name_to_id.get(raw_dept, raw_dept)
        if dept_id == "Legal & Compliance":
            dept_id = "LEGAL"
        elif dept_id == "Executive Office":
            dept_id = "EXEC"

        raw_tags = [t.strip() for t in row['tags'].split(',')]
        tags_json = json.dumps(raw_tags, ensure_ascii=False)
        
        # Get original content from Excel
        full_content = excel_docs.get(doc_id, "")
        
        sql_statements.append(
            f"INSERT INTO documents (id, document_id, title, department_id, classification, owner, "
            f"last_updated, tags, language, word_count, content, status) VALUES ("
            f"'{u}', {clean_sql_val(doc_id)}, {clean_sql_val(row['title'])}, "
            f"'{dept_id}', {clean_sql_val(row['classification'])}, {clean_sql_val(row['owner'])}, "
            f"'{row['last_updated']}', '{tags_json}'::jsonb, {clean_sql_val(row['language'])}, "
            f"{int(row['word_count'])}, {clean_sql_val(full_content)}, 'Active');"
        )
        
        # Chunking original Excel content
        lines = full_content.split('\n')
        chunks = []
        current_chunk_lines = []
        
        for line in lines:
            header_match = re.match(r'^(#{1,6})\s+(.*)$', line)
            if header_match:
                if current_chunk_lines:
                    chunks.append('\n'.join(current_chunk_lines).strip())
                    current_chunk_lines = []
            current_chunk_lines.append(line)
        if current_chunk_lines:
            chunks.append('\n'.join(current_chunk_lines).strip())
            
        for idx, c in enumerate(chunks):
            total_chunks_count += 1
            
            # Resolve section name from the first line of the chunk
            first_line = c.split('\n')[0].strip()
            header_match = re.match(r'^(#{1,6})\s+(.*)$', first_line)
            if header_match:
                section = header_match.group(2).strip()
            else:
                section = row['title']
                
            h = hashlib.sha256(c.encode('utf-8')).hexdigest()
            h_strip = hashlib.sha256(c.strip().encode('utf-8')).hexdigest()
            
            embedding_val = 'NULL'
            chunk_uuid = str(uuid.uuid4())
            
            emb_data = embeddings.get((doc_id, h)) or embeddings.get((doc_id, h_strip))
            if emb_data:
                matched_chunks_count += 1
                embedding_val = f"'{list(emb_data['embedding'])}'"
                # Use deterministic UUID from chunk_id
                chunk_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, emb_data['chunk_id']))
            else:
                print(f"WARNING: No embedding match for {doc_id} chunk {idx}")
                
            sql_statements.append(
                f"INSERT INTO chunks (id, document_id, chunk_index, section, content, embedding) VALUES ("
                f"'{chunk_uuid}', '{u}', {idx}, {clean_sql_val(section)}, {clean_sql_val(c)}, {embedding_val});"
            )

    print(f"Total chunks: {total_chunks_count}, Matched with embeddings: {matched_chunks_count}")

    # Insert Public Evaluation Cases
    sql_statements.append("\n-- Seeding public evaluation cases")
    for row in eval_rows:
        raw_ids = [d.strip() for d in row['expected_document_id'].split(';')]
        ids_json = json.dumps(raw_ids, ensure_ascii=False)
        
        sql_statements.append(
            f"INSERT INTO public_evaluation_cases (id, question_id, category, user_id, question, "
            f"expected_permission, expected_document_ids, answer_type, difficulty) VALUES ("
            f"gen_random_uuid(), {clean_sql_val(row['question_id'])}, {clean_sql_val(row['category'])}, "
            f"{clean_sql_val(row['user_id'])}, {clean_sql_val(row['question_vi'])}, "
            f"{clean_sql_val(row['expected_permission'])}, '{ids_json}'::jsonb, "
            f"{clean_sql_val(row['answer_type'])}, {clean_sql_val(row['difficulty'])});"
        )

    sql_statements.append("\nCOMMIT;")

    with open('/home/elior/Documents/aabw_tascotrack_p1/database/seeds/seed.sql', 'w', encoding='utf-8') as f:
        f.write('\n'.join(sql_statements))
        f.write('\n')

    print("Success! seed.sql created with embedded vectors.")

if __name__ == '__main__':
    main()

user_template = """USER QUESTION: {user_question}

VALIDATION CHECKLIST (complete before generating SQL):

1. What tables are needed? [LIST THEM]
2. Are they in ALLOWED TABLES? [CHECK EACH]
3. What columns are needed? [LIST THEM]
4. Are they in table's ALLOWED COLUMNS? [CHECK EACH]
5. What JOINs are needed? [LIST THEM]
6. Are they in ALLOWED RELATIONSHIPS? [CHECK EACH]

If ALL checks pass → Generate SQL
If ANY check fails → Return ERROR with specific reason

Generate your response:"""

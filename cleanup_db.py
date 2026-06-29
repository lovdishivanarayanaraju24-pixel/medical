import sqlite3

conn = sqlite3.connect('medvault.db')
c = conn.cursor()
c.execute("DELETE FROM test_results WHERE report_id IN (SELECT id FROM reports WHERE json_extract(structured_data, '$.patient.name') = 'Information Field Details Patient' OR raw_ocr_text = '' OR doctor LIKE '%ation Doctor%')")
c.execute("DELETE FROM medications WHERE report_id IN (SELECT id FROM reports WHERE json_extract(structured_data, '$.patient.name') = 'Information Field Details Patient' OR raw_ocr_text = '' OR doctor LIKE '%ation Doctor%')")
c.execute("DELETE FROM reports WHERE json_extract(structured_data, '$.patient.name') = 'Information Field Details Patient' OR raw_ocr_text = '' OR doctor LIKE '%ation Doctor%'")
conn.commit()
conn.close()
print("Cleaned up corrupted reports.")

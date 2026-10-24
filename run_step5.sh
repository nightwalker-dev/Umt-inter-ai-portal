#!/bin/bash
echo "# Step 5 - Database Analysis Log" > audit/step5_db_log.txt

echo -e "\n--- Checking Indexes ---" >> audit/step5_db_log.txt
grep -i "CREATE INDEX" 001_initial_schema.sql >> audit/step5_db_log.txt || echo "No explicit CREATE INDEX found" >> audit/step5_db_log.txt

echo -e "\n--- Checking Constraints ---" >> audit/step5_db_log.txt
grep -i "CONSTRAINT" 001_initial_schema.sql >> audit/step5_db_log.txt || true

echo -e "\n--- Checking Seed Script (for weak passwords/real data) ---" >> audit/step5_db_log.txt
grep -i "INSERT INTO" 001_initial_schema.sql >> audit/step5_db_log.txt || true

All queries operate on the applicants table loaded via load_data.py. Each function executes a SQL statement using a psycopg3 connection passed from the Flask application.



Question 1 — How many applicants applied for Fall 2026?

SQL Used

SELECT COUNT(*) FROM applicants
WHERE term = 'Fall 2026';


Explanation

This query counts the total number of records in the applicants table where the term column equals 'Fall 2026'. The COUNT(*) aggregate function returns the number of matching rows. This directly answers the question by computing the total number of applicants for that specific admission cycle.

Question 2 — What percentage of applicants are international?

SQL Used

SELECT ROUND(
    100.0 * SUM(CASE WHEN us_or_international = 'International' THEN 1 ELSE 0 END)
    / COUNT(*), 2
)
FROM applicants
WHERE us_or_international IS NOT NULL;


Explanation

This query calculates the percentage of applicants classified as international. The CASE statement assigns 1 to international applicants and 0 otherwise, and SUM() counts the total number of international applicants. Dividing by COUNT(*) (total non-null applicants) and multiplying by 100 produces a percentage, which is rounded to two decimal places.

Question 3 — What are the average GPA and GRE scores?

SQL Used

SELECT
    ROUND(AVG(gpa)::numeric, 2),
    ROUND(AVG(gre)::numeric, 2),
    ROUND(AVG(gre_v)::numeric, 2),
    ROUND(AVG(gre_aw)::numeric, 2)
FROM applicants;


Explanation

This query computes the average GPA and GRE scores across all applicants. The AVG() function calculates the mean for each numeric column, and each value is cast to numeric and rounded to two decimal places for presentation. The result provides overall academic performance statistics for the dataset.

Question 4 — What is the average GPA of American applicants for Fall 2026?

SQL Used

SELECT ROUND(AVG(gpa)::numeric, 2)
FROM applicants
WHERE term = 'Fall 2026'
  AND us_or_international = 'American';


Explanation

This query filters the dataset to include only applicants for Fall 2026 who are classified as American. The AVG(gpa) function calculates the mean GPA for this subset. Rounding ensures consistent formatting. The result represents the average GPA for domestic applicants in that admission cycle.

Question 5 — What percentage of Fall 2026 applicants were accepted?

SQL Used

SELECT ROUND(
    100.0 * SUM(CASE WHEN status ILIKE 'accepted%' THEN 1 ELSE 0 END)
    / COUNT(*), 2
)
FROM applicants
WHERE term = 'Fall 2026';


Explanation

This query computes the acceptance rate for Fall 2026 applicants. The CASE expression counts records where the status field begins with "accepted" (case-insensitive via ILIKE). Dividing the number of accepted applicants by the total number of Fall 2026 applicants and multiplying by 100 yields the acceptance percentage.

Question 6 — What is the average GPA of accepted Fall 2026 applicants?

SQL Used

SELECT ROUND(AVG(gpa)::numeric, 2)
FROM applicants
WHERE term = 'Fall 2026'
  AND status ILIKE 'accepted%';


Explanation

This query calculates the average GPA for applicants accepted in Fall 2026. The WHERE clause restricts records to those both in the specified term and with a status beginning with "accepted." The AVG() function computes the mean GPA for this admitted group.

Question 7 — How many Master's Computer Science applicants mentioned Johns Hopkins?

SQL Used

SELECT COUNT(*)
FROM applicants
WHERE degree = 'Masters'
  AND program ILIKE '%computer science%'
  AND comments ILIKE '%johns hopkins%';


Explanation

This query counts applicants pursuing a Master’s degree in Computer Science who mentioned “Johns Hopkins” in their comments. The ILIKE operator enables case-insensitive pattern matching using wildcard %. This identifies records referencing Johns Hopkins within free-text comment data.

Question 8 — How many PhD Computer Science applicants (2026) were accepted to selected top universities?

SQL Used

SELECT COUNT(*)
FROM applicants
WHERE term LIKE '%2026%'
  AND status ILIKE 'accepted%'
  AND degree = 'PhD'
  AND program ILIKE '%computer science%'
  AND (
       comments ILIKE '%georgetown%'
    OR comments ILIKE '%mit%'
    OR comments ILIKE '%stanford%'
    OR comments ILIKE '%carnegie mellon%'
  );


Explanation

This query counts accepted PhD Computer Science applicants in 2026 who referenced specific universities (Georgetown, MIT, Stanford, or Carnegie Mellon) in their comments. Multiple ILIKE conditions combined with OR allow matching against several institutions. The filters ensure the results are restricted to accepted PhD CS applicants in the relevant admission year.

Question 9 — LLM-Generated vs Raw Field Comparison

SQL Used

SELECT COUNT(*)
FROM applicants
WHERE term LIKE '%2026%'
  AND status ILIKE 'accepted%'
  AND degree = 'PhD'
  AND llm_generated_program ILIKE '%computer science%'
  AND (
       llm_generated_university ILIKE '%georgetown%'
    OR llm_generated_university ILIKE '%mit%'
    OR llm_generated_university ILIKE '%stanford%'
    OR llm_generated_university ILIKE '%carnegie mellon%'
  );


Explanation

This query mirrors Question 8 but uses the structured fields generated by the LLM (llm_generated_program and llm_generated_university) instead of searching raw comments. This allows comparison between free-text parsing and LLM-standardized fields. The result demonstrates how structured extraction may improve query reliability and consistency.
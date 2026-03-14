# AIA KMS Test Cases

This directory contains test documents and automated testing scripts for the AIA KMS system.

## Test Documents

### Insurance Company Scenario

The test documents simulate an insurance company offering life and health insurance products.

1. **General_Insurance_Products.docx**
   - Intent Space: General
   - Content: Insurance products, services, customer support
   - Format: Word document
   - Sections: Life insurance, Health insurance, Customer service, Contact info

2. **Finance_Budget_Report.docx**
   - Intent Space: Finance
   - Content: Annual budget with complex tables
   - Format: Word document with multi-level tables
   - Features: Department budget summary, Expense breakdown by category
   - Tables: 2 complex tables with totals and percentages

3. **HR_Policies.docx**
   - Intent Space: HR
   - Content: Human resources policies and procedures
   - Format: Word document
   - Sections: Employee benefits, Leave policies, Remote work, Performance review

4. **Legal_Compliance.xlsx**
   - Intent Space: Legal
   - Content: Regulatory compliance and contract templates
   - Format: Excel workbook with 2 sheets
   - Sheet 1: Regulatory Compliance (5 regulations)
   - Sheet 2: Contract Templates (5 template types)

## Configuration Files

5. **INTENT_SPACE_CONFIG.md**
   - Complete intent space configurations for all 5 departments
   - Keywords for each intent space
   - 50 test questions (10 per intent space)
   - Performance requirements: All queries must complete within 3 seconds
   - Test execution checklist

## Testing Scripts

### Automated Test Script

**auto_test.py** - Full automated testing suite

Features:
- Automatically creates all 5 intent spaces
- Uploads test documents to appropriate intent spaces
- Executes 50 test queries (10 per intent space)
- Measures response time for each query
- Validates 3-second response time requirement
- Generates detailed test reports (Markdown and JSON)
- Provides performance statistics by intent space

#### Prerequisites

1. Backend service must be running:
   ```bash
   python backend/main.py
   ```

2. Required Python packages:
   ```bash
   pip install requests
   ```

#### Running Tests

Execute all tests:
```bash
python testcases/auto_test.py
```

#### Test Report

After execution, two report files are generated:
- `TEST_REPORT_YYYYMMDD_HHMMSS.md` - Human-readable Markdown report
- `TEST_REPORT_YYYYMMDD_HHMMSS.json` - Machine-readable JSON report

#### Report Contents

**Overall Summary**:
- Total tests executed
- Success rate percentage
- Queries within 3 seconds
- Average response time

**Performance by Intent Space**:
- Tests per intent space
- Success rate per intent space
- Within 3s rate per intent space
- Average and max response times

**Detailed Results**:
- Individual query results
- Response time for each query
- Success/failure status
- Error notes

## Test Execution Manual

If you prefer manual testing, follow these steps:

### Step 1: Start Services

1. Start backend:
   ```bash
   python backend/main.py
   ```

2. Start frontend (optional):
   ```bash
   streamlit run frontend/app.py
   ```

### Step 2: Create Intent Spaces

Access http://localhost:8501 and navigate to "Intent Configuration" page.

Create the following intent spaces:

1. **General**
   - Description: General insurance products, services, and company information for customers and prospects
   - Keywords: insurance, life insurance, term, whole life, universal life, health insurance, medical, prescription, drug, coverage, premium, benefit, policy, customer service, support, claims, hotline, account, mobile app, contact, phone, email, website, sales team

2. **Finance**
   - Description: Financial policies, budget management, expense tracking, and financial reporting
   - Keywords: budget, expense, cost, financial, fiscal, quarterly, annual report, department budget, allocation, Q1, Q2, Q3, Q4, forecast, expense breakdown, category, personnel, technology, software, office, facilities, professional services, travel, entertainment, YTD actual, spend, cost center, variance, projection, financial analysis

3. **HR**
   - Description: Human resources policies, employee benefits, leave policies, performance management, and workplace procedures
   - Keywords: HR, human resources, employee, benefits, package, health insurance, dental, vision, 401k, retirement, matching, paid time off, vacation, sick leave, holiday, leave policy, accrual, remote work, work from home, manager approval, performance review, appraisal, feedback, self-assessment, goal setting, rating

4. **Legal**
   - Description: Legal compliance, regulatory requirements, contract templates, and policy documentation
   - Keywords: legal, compliance, regulation, regulatory, GDPR, Sarbanes-Oxley, SOX, HIPAA, PCI-DSS, CCPA, data protection, privacy, security, contract, agreement, template, NDA, MSA, employment agreement, terms of service, privacy policy, terms and conditions, legal counsel, audit, reporting, controls, due date, owner, approval

5. **Marketing**
   - Description: Marketing strategies, campaign planning, brand management, and promotional activities
   - Keywords: marketing, advertising, promotion, campaign, brand, brand management, digital marketing, social media, content marketing, email marketing, SEO, campaign planning, budget allocation, ROI, conversion, leads, prospects, brand guidelines, brand identity, messaging, positioning, marketing strategy, market research, target audience, customer acquisition, retention, loyalty

### Step 3: Upload Documents

Navigate to "Knowledge Base Management" page and upload:

1. Upload `General_Insurance_Products.docx` → Assign to "General" intent space
2. Upload `Finance_Budget_Report.docx` → Assign to "Finance" intent space
3. Upload `HR_Policies.docx` → Assign to "HR" intent space
4. Upload `Legal_Compliance.xlsx` → Assign to "Legal" intent space

Wait for all documents to be processed (status should show "Processed").

### Step 4: Test Queries

Use the Dashboard's query testing interface or refer to `INTENT_SPACE_CONFIG.md` for all test questions.

Test each question and verify:
- [ ] Response is relevant and accurate
- [ ] Response completes within 3 seconds
- [ ] Correct intent space was classified
- [ ] Citations are included with source documents

## Performance Requirements

All test queries must complete within **3 seconds**.

### Performance Metrics to Monitor

- **Response Time**: Time from query submission to response
- **Success Rate**: Percentage of queries that return valid responses
- **Intent Classification Accuracy**: Correct intent space classification
- **Chunk Retrieval**: Relevant chunks are retrieved from documents

### Expected Performance Targets

| Metric | Target | Acceptable |
|---------|---------|-------------|
| Response Time | < 2s | < 3s |
| Success Rate | 100% | > 95% |
| Intent Accuracy | > 90% | > 80% |

## Troubleshooting

### Backend Not Running
Error: `Connection refused` or `Connection timeout`

Solution: Start the backend service:
```bash
python backend/main.py
```

### Document Processing Failed
Error: Document status shows "Error" or "Pending" for long time

Solution:
1. Check backend logs for errors
2. Verify file format is supported
3. Ensure file size is under limits (max 10MB)

### Slow Response Times
Error: Queries taking longer than 3 seconds

Solution:
1. Check system resources (CPU, memory)
2. Verify vector index is loaded correctly
3. Check DashScope API status
4. Review logs for performance bottlenecks

### Incorrect Intent Classification
Error: Queries classified to wrong intent space

Solution:
1. Verify intent space keywords are appropriate
2. Check classification confidence threshold
3. Consider adding more specific keywords
4. Clear intent classification cache

## Document Management Scripts

### Generate Test Documents

To regenerate all test documents:
```bash
python testcases/generate_test_docs.py
```

This will create:
- `General_Insurance_Products.docx`
- `HR_Policies.docx`
- `Finance_Budget_Report.docx`
- `Legal_Compliance.xlsx`

## Clean Up

To remove generated test files and reports:
```bash
# Windows
del testcases\TEST_REPORT_*
del testcases\General_*.docx
del testcases\HR_*.docx
del testcases\Finance_*.docx
del testcases\Legal_*.xlsx

# Linux/Mac
rm testcases/TEST_REPORT_*
rm testcases/General_*.docx
rm testcases/HR_*.docx
rm testcases/Finance_*.docx
rm testcases/Legal_*.xlsx
```

---

**Version**: 1.0
**Last Updated**: 2025-03-14

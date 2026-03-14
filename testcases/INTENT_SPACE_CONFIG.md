# Intent Space Configuration and Test Questions

This document contains the configuration for all intent spaces and test questions for AIA KMS system.

## Intent Space Configurations

### 1. General

**Description**: General insurance products, services, and company information for customers and prospects

**Keywords**:
- insurance, life insurance, term, whole life, universal life, health insurance
- medical, prescription, drug, coverage, premium, benefit, policy
- customer service, support, claims, hotline, account, mobile app
- contact, phone, email, website, sales team

**Test Questions**:
1. What types of life insurance do you offer?
2. How much does term life insurance cost?
3. What is the difference between whole life and universal life?
4. Do you offer health insurance?
5. How do I file a claim?
6. What is your 24/7 claims hotline number?
7. Can I access my policy online?
8. What prescription drug plans are available?
9. How do I contact customer service?
10. What are your office hours?

---

### 2. Finance

**Description**: Financial policies, budget management, expense tracking, and financial reporting

**Keywords**:
- budget, expense, cost, financial, fiscal, quarterly, annual report
- department budget, allocation, Q1, Q2, Q3, Q4, forecast
- expense breakdown, category, personnel, technology, software, office
- facilities, professional services, travel, entertainment, YTD actual
- spend, cost center, variance, projection, financial analysis

**Test Questions**:
1. What is the total annual budget for FY 2025?
2. How much is allocated to the Sales & Marketing department?
3. What is the Q4 budget for Underwriting?
4. What percentage of total budget goes to personnel costs?
5. How much is the YTD actual spend on technology?
6. What is the total budget for Q1 across all departments?
7. Which department has the highest annual budget?
8. What is the difference between Q1 and Q4 budget for IT & Operations?
9. What are the main expense categories?
10. How much travel & entertainment budget is allocated annually?

---

### 3. HR

**Description**: Human resources policies, employee benefits, leave policies, performance management, and workplace procedures

**Keywords**:
- HR, human resources, employee, benefits, package, health insurance, dental, vision
- 401k, retirement, matching, paid time off, vacation, sick leave, holiday
- leave policy, accrual, remote work, work from home, manager approval
- performance review, appraisal, feedback, self-assessment, goal setting, rating

**Test Questions**:
1. What health insurance benefits are included?
2. How many vacation days do I get per year?
3. What is the company 401(k) matching rate?
4. What are the requirements for remote work?
5. How many sick days do full-time employees get?
6. When is the performance review conducted?
7. What are the quarterly performance review milestones?
8. How much vacation do I accrue after 5 years?
9. What are the paid time off holidays?
10. Can I use sick leave for medical appointments?

---

### 4. Legal

**Description**: Legal compliance, regulatory requirements, contract templates, and policy documentation

**Keywords**:
- legal, compliance, regulation, regulatory, GDPR, Sarbanes-Oxley, SOX
- HIPAA, PCI-DSS, CCPA, data protection, privacy, security
- contract, agreement, template, NDA, MSA, employment agreement
- terms of service, privacy policy, terms and conditions, legal counsel
- audit, reporting, controls, due date, owner, approval

**Test Questions**:
1. What regulations must the company comply with?
2. What is the status of Sarbanes-Oxley compliance?
3. When is the HIPAA compliance due date?
4. What contract templates are available?
5. Who owns the GDPR compliance project?
6. What is the latest version of the NDA template?
7. What are the PCI-DSS requirements for payment card security?
8. Who approves the MSA contracts?
9. What is the CCPA compliance status?
10. When was the Privacy Policy last updated?

---

### 5. Marketing

**Description**: Marketing strategies, campaign planning, brand management, and promotional activities

**Keywords**:
- marketing, advertising, promotion, campaign, brand, brand management
- digital marketing, social media, content marketing, email marketing, SEO
- campaign planning, budget allocation, ROI, conversion, leads, prospects
- brand guidelines, brand identity, messaging, positioning, marketing strategy
- market research, target audience, customer acquisition, retention, loyalty

**Test Questions**:
1. What are our main marketing strategies?
2. How do we measure marketing campaign success?
3. What social media platforms do we use?
4. What is our brand positioning strategy?
5. How do we acquire new customers?
6. What is the marketing budget allocation?
7. What content marketing channels do we use?
8. How do we measure customer lifetime value?
9. What are our retention strategies?
10. What is our brand voice and tone guidelines?

---

## Performance Requirements

**All test questions must return results within 3 seconds**

To ensure <3s response time:
- Each question should be concise and specific
- Keywords in the question should match intent space keywords
- Questions should be based on the uploaded test documents
- Avoid ambiguous or overly complex questions

---

## Test Execution Checklist

### Document Upload
- [ ] Upload `General_Insurance_Products.docx` to General intent space
- [ ] Upload `Finance_Budget_Report.docx` to Finance intent space
- [ ] Upload `HR_Policies.docx` to HR intent space
- [ ] Upload `Legal_Compliance.xlsx` to Legal intent space

### Intent Space Creation
- [ ] Create General intent space with specified keywords
- [ ] Create Finance intent space with specified keywords
- [ ] Create HR intent space with specified keywords
- [ ] Create Legal intent space with specified keywords
- [ ] Create Marketing intent space with specified keywords

### Testing
- [ ] Test all 10 questions for General intent (target: <3s)
- [ ] Test all 10 questions for Finance intent (target: <3s)
- [ ] Test all 10 questions for HR intent (target: <3s)
- [ ] Test all 10 questions for Legal intent (target: <3s)
- [ ] Test all 10 questions for Marketing intent (target: <3s)

### Performance Validation
- [ ] Record response time for each question
- [ ] Verify all questions complete within 3 seconds
- [ ] Document any questions exceeding 3 seconds
- [ ] Analyze patterns for slow responses
- [ ] Optimize if necessary

---

## Expected Outcomes

- All 5 intent spaces configured with appropriate keywords
- All test documents uploaded and processed successfully
- All 50 test questions return relevant results
- All responses complete within 3 seconds
- System correctly classifies queries to appropriate intent spaces
- Chunk management features work correctly for all documents

---

**Document Version**: 1.0
**Created**: 2025-03-14
**Total Test Questions**: 50 (10 per intent space)

# Datadog Analysis Guide - Thai Political Party Policies

## Overview

This guide provides queries, visualizations, and analysis ideas for the 587 Thai political party policies now available in Datadog.

**Base Query:** `source:custom-log service:th-election-policy version:20260129-0945`

## Available Attributes

### Party Information
- `@party_number` - Party number (1-57)
- `@party_name` - Party name in Thai

### Policy Details
- `@policy_seq` - Policy sequence number
- `@policy_category` - Policy category (15 categories)
- `@policy_name` - Policy name/title
- `@budget_baht` - Budget in Baht (integer)
- `@funding_source` - Funding source description
- `@cost_effectiveness` - Cost-effectiveness analysis
- `@benefits` - Benefits description
- `@impacts` - Impact analysis
- `@risks` - Risk assessment

## Analysis Ideas

### 1. Budget Analysis

#### Total Budget by Party
**Query:**
```
source:custom-log service:th-election-policy 
| stats sum(@budget_baht) by @party_name
| sort -sum(@budget_baht)
```

**Visualization:** Bar chart
**Insight:** Which parties have the most expensive policy platforms?

#### Budget Distribution by Category
**Query:**
```
source:custom-log service:th-election-policy 
| stats sum(@budget_baht) by @policy_category
| sort -sum(@budget_baht)
```

**Visualization:** Pie chart or bar chart
**Insight:** Which policy areas receive the most funding across all parties?

#### High-Budget Policies (>100 billion Baht)
**Query:**
```
source:custom-log service:th-election-policy @budget_baht:>100000000000
| sort -@budget_baht
```

**Visualization:** Table with party_name, policy_name, budget_baht
**Insight:** Identify the most expensive individual policies

#### Budget vs Policy Count
**Query:**
```
source:custom-log service:th-election-policy 
| stats count(), sum(@budget_baht) by @party_name
```

**Visualization:** Scatter plot (count vs sum)
**Insight:** Do parties with more policies have higher total budgets?

### 2. Policy Category Analysis

#### Policy Count by Category
**Query:**
```
source:custom-log service:th-election-policy 
| stats count() by @policy_category
| sort -count()
```

**Visualization:** Bar chart
**Insight:** Which policy areas are most popular across parties?

#### Parties by Category Focus
**Query:**
```
source:custom-log service:th-election-policy @policy_category:เศรษฐกิจและการค้า
| stats count() by @party_name
| sort -count()
```

**Visualization:** Bar chart
**Insight:** Which parties focus most on economy/trade?

#### Category Distribution per Party
**Query:**
```
source:custom-log service:th-election-policy @party_number:9
| stats count() by @policy_category
```

**Visualization:** Pie chart
**Insight:** What's the policy focus distribution for a specific party?

### 3. Party Comparison

#### Policy Count by Party
**Query:**
```
source:custom-log service:th-election-policy 
| stats count() by @party_name
| sort -count()
```

**Visualization:** Bar chart (horizontal)
**Insight:** Which parties have the most comprehensive platforms?

#### Top 5 Parties by Budget
**Query:**
```
source:custom-log service:th-election-policy 
| stats sum(@budget_baht) by @party_name
| sort -sum(@budget_baht)
| limit 5
```

**Visualization:** Bar chart
**Insight:** Most expensive party platforms

#### Parties with Zero-Budget Policies
**Query:**
```
source:custom-log service:th-election-policy @budget_baht:0
| stats count() by @party_name
| sort -count()
```

**Visualization:** Bar chart
**Insight:** Which parties have more unfunded policies?

### 4. Specific Category Deep Dives

#### Healthcare Policies (สาธารณสุข)
**Query:**
```
source:custom-log service:th-election-policy @policy_category:สาธารณสุข
| stats count(), sum(@budget_baht), avg(@budget_baht) by @party_name
```

**Visualization:** Table
**Insight:** Healthcare policy comparison across parties

#### Infrastructure Policies (โครงสร้างพื้นฐาน)
**Query:**
```
source:custom-log service:th-election-policy @policy_category:โครงสร้างพื้นฐาน
| stats sum(@budget_baht) by @party_name
| sort -sum(@budget_baht)
```

**Visualization:** Bar chart
**Insight:** Infrastructure investment priorities

#### Social Welfare (สวัสดิการสังคม)
**Query:**
```
source:custom-log service:th-election-policy @policy_category:สวัสดิการสังคม
| stats count() by @party_name
| sort -count()
```

**Visualization:** Bar chart
**Insight:** Which parties prioritize social welfare?

### 5. Budget Ranges

#### Policies by Budget Range
**Query:**
```
source:custom-log service:th-election-policy 
| eval budget_range = if(@budget_baht == 0, "No budget",
    if(@budget_baht < 1000000000, "< 1B",
    if(@budget_baht < 10000000000, "1-10B",
    if(@budget_baht < 100000000000, "10-100B",
    "> 100B"))))
| stats count() by budget_range
```

**Visualization:** Pie chart
**Insight:** Distribution of policy costs

#### Average Budget by Category
**Query:**
```
source:custom-log service:th-election-policy @budget_baht:>0
| stats avg(@budget_baht) by @policy_category
| sort -avg(@budget_baht)
```

**Visualization:** Bar chart
**Insight:** Which categories have the most expensive policies on average?

### 6. Text Analysis

#### Policies Mentioning Specific Keywords
**Query:**
```
source:custom-log service:th-election-policy @policy_name:*ดิจิทัล*
```

**Insight:** Digital transformation policies

**Query:**
```
source:custom-log service:th-election-policy @policy_name:*เกษตร*
```

**Insight:** Agriculture-related policies

**Query:**
```
source:custom-log service:th-election-policy @benefits:*ลดหนี้*
```

**Insight:** Debt reduction benefits

### 7. Comparative Analysis

#### Party 9 vs Party 27 (Largest Parties)
**Query:**
```
source:custom-log service:th-election-policy @party_number:(9 OR 27)
| stats count(), sum(@budget_baht) by @party_number, @policy_category
```

**Visualization:** Grouped bar chart
**Insight:** Compare policy focus and budgets

#### Top 3 Parties - Category Breakdown
**Query:**
```
source:custom-log service:th-election-policy @party_number:(9 OR 27 OR 46)
| stats count() by @party_name, @policy_category
```

**Visualization:** Stacked bar chart
**Insight:** Policy distribution across top parties

### 8. Funding Source Analysis

#### Policies by Funding Source Type
**Query:**
```
source:custom-log service:th-election-policy @funding_source:*งบประมาณ*
| stats count()
```

**Insight:** Government budget-funded policies

**Query:**
```
source:custom-log service:th-election-policy @funding_source:*เอกชน*
| stats count()
```

**Insight:** Private sector involvement

### 9. Risk Analysis

#### Policies with High Risk
**Query:**
```
source:custom-log service:th-election-policy @risks:*ความเสี่ยง*
| stats count() by @policy_category
```

**Visualization:** Bar chart
**Insight:** Which categories have more risky policies?

#### Zero-Budget Policies with Risks
**Query:**
```
source:custom-log service:th-election-policy @budget_baht:0 @risks:*
| stats count() by @party_name
```

**Insight:** Unfunded but risky policies

### 10. Advanced Analytics

#### Budget Efficiency Score
**Query:**
```
source:custom-log service:th-election-policy @budget_baht:>0
| eval efficiency = len(@benefits) / (@budget_baht / 1000000000)
| stats avg(efficiency) by @policy_category
```

**Insight:** Which categories provide more benefits per billion Baht?

#### Policy Complexity (by text length)
**Query:**
```
source:custom-log service:th-election-policy 
| eval complexity = len(@policy_name) + len(@benefits) + len(@impacts)
| stats avg(complexity) by @policy_category
```

**Insight:** Which categories have more detailed policies?

## Dashboard Ideas

### Dashboard 1: Executive Overview
- Total policies count (big number)
- Total budget sum (big number)
- Policy count by category (pie chart)
- Budget by category (bar chart)
- Top 10 parties by policy count (bar chart)
- Top 10 parties by budget (bar chart)

### Dashboard 2: Party Comparison
- Policy count comparison (grouped bar)
- Budget comparison (grouped bar)
- Category distribution (stacked bar)
- Budget vs policy count (scatter plot)

### Dashboard 3: Category Deep Dive
- Healthcare policies (count, budget, parties)
- Education policies (count, budget, parties)
- Infrastructure policies (count, budget, parties)
- Social welfare policies (count, budget, parties)

### Dashboard 4: Budget Analysis
- Budget distribution (histogram)
- Budget by category (treemap)
- High-budget policies (table)
- Zero-budget policies (count by party)

### Dashboard 5: Text Analytics
- Most common keywords in policy names
- Benefit themes analysis
- Risk patterns by category
- Funding source distribution

## Useful Facets

Create these facets in Datadog for easier filtering:

1. `@party_number` - Numeric
2. `@party_name` - String
3. `@policy_category` - String (with values)
4. `@budget_baht` - Numeric
5. `@policy_seq` - Numeric

## Example Queries for Specific Questions

### Q: Which party has the most expensive healthcare policies?
```
source:custom-log service:th-election-policy @policy_category:สาธารณสุข
| stats sum(@budget_baht) by @party_name
| sort -sum(@budget_baht)
| limit 1
```

### Q: How many parties have education policies?
```
source:custom-log service:th-election-policy @policy_category:การศึกษา
| stats uniqueCount(@party_number)
```

### Q: What's the average budget for infrastructure projects?
```
source:custom-log service:th-election-policy @policy_category:โครงสร้างพื้นฐาน @budget_baht:>0
| stats avg(@budget_baht)
```

### Q: Which policies mention "ดิจิทัล" (digital)?
```
source:custom-log service:th-election-policy @policy_name:*ดิจิทัล*
| stats count() by @party_name
```

### Q: Total budget for all parties combined?
```
source:custom-log service:th-election-policy
| stats sum(@budget_baht)
```

## Monitor Ideas

### Alert 1: New Policy Data Ingested
**Condition:** `source:custom-log service:th-election-policy`  
**Threshold:** Count > 0 in last 5 minutes  
**Use case:** Know when new data is loaded

### Alert 2: High-Budget Policy Detected
**Condition:** `@budget_baht:>500000000000`  
**Use case:** Track mega-projects

## Export Options

### Export to CSV from Datadog
1. Run query in Log Explorer
2. Click "Export" → "Download as CSV"
3. Use for further analysis in Excel/Python

### Export to Dashboard
1. Save query as widget
2. Add to dashboard
3. Share with stakeholders

## Tips for Analysis

1. **Use time range:** Even though data is static, use "Past 1 day" to see all data
2. **Combine filters:** `@party_number:9 @policy_category:เศรษฐกิจและการค้า`
3. **Use wildcards:** `@policy_name:*โครงสร้างพื้นฐาน*`
4. **Group by multiple fields:** `by @party_name, @policy_category`
5. **Calculate percentages:** Use formulas in dashboards

## Next Steps

1. ✅ Data is in Datadog
2. 📊 Create dashboards for visualization
3. 📈 Run analysis queries
4. 📝 Generate insights
5. 🎯 Share findings with stakeholders

## Sample Analysis Questions

### Political Strategy
- Which parties focus on social welfare vs economic growth?
- Do parties with more policies have higher budgets?
- Which categories are most/least popular?

### Budget Priorities
- What's the total proposed spending across all parties?
- Which categories get the most funding?
- Are there unfunded policy areas?

### Policy Patterns
- Do certain parties share similar policy focuses?
- Which policies are unique vs common?
- What are the most expensive policy types?

### Risk Assessment
- Which categories have the highest risk mentions?
- Do high-budget policies have more risks?
- Which parties acknowledge more risks?

---

**Data Version:** 20260129-0945  
**Total Policies:** 587  
**Total Parties:** 51  
**Query Base:** `source:custom-log service:th-election-policy`

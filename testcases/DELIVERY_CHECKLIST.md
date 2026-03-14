# Test Cases Delivery Checklist

## ✅ 任务完成状态

### 1. 测试文档生成

| Intent Space | 文件类型 | 文件名 | 状态 | 说明 |
|--------------|----------|---------|------|------|
| General | Word | `General_Insurance_Products.docx` | ✅ 完成 | 保险产品、服务、客户支持信息 |
| Finance | Word (复杂表格) | `Finance_Budget_Report.docx` | ✅ 完成 | 年度预算报告，含两个复杂表格 |
| HR | Word | `HR_Policies.docx` | ✅ 完成 | 人力资源政策、福利、休假、绩效评估 |
| Legal | Excel (2 sheets) | `Legal_Compliance.xlsx` | ✅ 完成 | 法规合规和合同模板，2个工作表 |

### 2. Intent Space 配置

| Intent Space | 配置文件 | 关键词数量 | 测试问题数量 | 状态 |
|--------------|----------|------------|--------------|------|
| General | ✅ 已配置 | 20 个 | 10 个 | ✅ 完成 |
| Finance | ✅ 已配置 | 25 个 | 10 个 | ✅ 完成 |
| HR | ✅ 已配置 | 25 个 | 10 个 | ✅ 完成 |
| Legal | ✅ 已配置 | 25 个 | 10 个 | ✅ 完成 |
| Marketing | ✅ 已配置 | 25 个 | 10 个 | ✅ 完成 |

**配置文件**: `INTENT_SPACE_CONFIG.md`
**总测试问题**: 50 个
**性能要求**: 所有查询必须在 3 秒内完成

### 3. 自动化测试脚本

| 脚本名称 | 功能 | 状态 |
|----------|------|------|
| `auto_test.py` | 全自动化测试套件 | ✅ 完成 |
| `generate_test_docs.py` | 文档生成脚本 | ✅ 完成 |

**auto_test.py 功能**:
- ✅ 自动创建 5 个 Intent Space
- ✅ 上传测试文档到相应的 Intent Space
- ✅ 执行 50 个查询测试（每部门 10 个）
- ✅ 测量每个查询的响应时间
- ✅ 验证 3 秒响应时间要求
- ✅ 生成详细测试报告（Markdown + JSON）
- ✅ 按部门统计性能指标

### 4. 文档和说明

| 文件名 | 内容 | 状态 |
|--------|------|------|
| `README.md` | 测试用例使用说明 | ✅ 完成 |
| `TEST_CASES_SUMMARY.md` | 测试用例生成总结 | ✅ 完成 |
| `INTENT_SPACE_CONFIG.md` | Intent Space 配置和测试问题 | ✅ 完成 |

## 文件清单

### 测试文档 (4 个)
```
✅ General_Insurance_Products.docx
✅ Finance_Budget_Report.docx
✅ HR_Policies.docx
✅ Legal_Compliance.xlsx
```

### 配置文件 (3 个)
```
✅ INTENT_SPACE_CONFIG.md
✅ README.md
✅ TEST_CASES_SUMMARY.md
```

### 脚本文件 (2 个)
```
✅ generate_test_docs.py
✅ auto_test.py
```

**总计**: 9 个文件

## 保险业务场景

模拟的保险公司业务：
- 主要经营寿险和健康险产品
- 涵盖 5 个核心业务部门
- 包含复杂的财务表格和合规文档
- 提供完整的人力资源政策
- 包含市场营销策略配置

## 执行步骤

### 步骤 1: 启动服务

```bash
# 启动后端
python backend/main.py

# 可选：启动前端
streamlit run frontend/app.py
```

### 步骤 2: 运行自动化测试

```bash
# 进入项目目录
cd "C:\Users\aries\CodeBuddy\AIA KMS"

# 运行自动化测试脚本
python testcases/auto_test.py
```

### 步骤 3: 查看测试报告

测试完成后，将在 `testcases/` 目录生成：

- `TEST_REPORT_YYYYMMDD_HHMMSS.md` - Markdown 格式报告
- `TEST_REPORT_YYYYMMDD_HHMMSS.json` - JSON 格式报告

### 步骤 4: 性能验证

检查报告中的关键指标：

- **总查询数**: 50
- **成功率**: 目标 100%
- **3秒内完成率**: 目标 100%
- **平均响应时间**: 目标 < 2000ms
- **最大响应时间**: 目标 < 3000ms

## 性能基准

| Intent Space | 预期响应时间 | 性能目标 |
|--------------|--------------|----------|
| General | < 2s | 高准确性，清晰响应 |
| Finance | < 2.5s | 复杂查询，需要处理表格数据 |
| HR | < 2s | 直接查询，快速响应 |
| Legal | < 2s | 法规查询，精确匹配 |
| Marketing | < 2s | 营销策略，快速检索 |

## 验证清单

### 文档上传验证
- [ ] `General_Insurance_Products.docx` 上传成功
- [ ] `Finance_Budget_Report.docx` 上传成功
- [ ] `HR_Policies.docx` 上传成功
- [ ] `Legal_Compliance.xlsx` 上传成功（验证 2 个 sheet）

### Intent Space 验证
- [ ] General intent space 创建成功，包含 20 个关键词
- [ ] Finance intent space 创建成功，包含 25 个关键词
- [ ] HR intent space 创建成功，包含 25 个关键词
- [ ] Legal intent space 创建成功，包含 25 个关键词
- [ ] Marketing intent space 创建成功，包含 25 个关键词

### 查询测试验证
- [ ] General: 10 个问题全部测试，响应 < 3s
- [ ] Finance: 10 个问题全部测试，响应 < 3s
- [ ] HR: 10 个问题全部测试，响应 < 3s
- [ ] Legal: 10 个问题全部测试，响应 < 3s
- [ ] Marketing: 10 个问题全部测试，响应 < 3s

### 性能报告验证
- [ ] Markdown 报告生成成功
- [ ] JSON 报告生成成功
- [ ] 所有 50 个查询结果记录
- [ ] 响应时间统计正确
- [ ] 成功率计算正确

## 故障排除

### 问题：后端未启动

**症状**: `Connection refused` 或 `Connection timeout`

**解决方案**:
```bash
python backend/main.py
```

### 问题：文档上传失败

**症状**: 文档状态显示 "Error"

**解决方案**:
1. 检查文件格式是否支持（.docx, .xlsx, .pdf）
2. 检查文件大小（最大 10MB）
3. 查看后端日志

### 问题：响应时间超过 3 秒

**症状**: 查询响应时间 > 3000ms

**解决方案**:
1. 检查系统资源（CPU、内存）
2. 验证向量索引已加载
3. 检查 DashScope API 状态
4. 查看性能报告中的慢查询模式

### 问题：查询无结果

**症状**: 返回 "No relevant information found"

**解决方案**:
1. 验证文档已成功上传并处理
2. 检查 Intent Space 关键词配置
3. 尝试简化查询
4. 查看向量索引状态

## 交付标准

### 所有任务必须满足的条件

✅ **测试文档**:
   - 4 个测试文档已创建
   - General (Word), Finance (含复杂表格的 Word), HR (Word), Legal (2 sheet Excel)
   - 所有文档包含保险相关内容

✅ **Intent Space 配置**:
   - 5 个部门配置文件已创建
   - 每个部门包含详细关键词列表
   - 每个部门包含 10 个测试问题
   - 总计 50 个测试问题
   - 所有问题设计为 3 秒内完成

✅ **自动化测试**:
   - 完整的自动化测试脚本已创建
   - 支持 API 自动化测试
   - 包含性能测和报告生成
   - 支持 Markdown 和 JSON 报告格式

✅ **文档**:
   - README.md 提供详细使用说明
   - TEST_CASES_SUMMARY.md 提供生成总结
   - DELIVERY_CHECKLIST.md 提供交付验证清单

---

**状态**: ✅ 所有任务已完成
**日期**: 2025-03-14
**测试文件数**: 4 个
**配置文件数**: 3 个
**脚本文件数**: 2 个
**总文件数**: 9 个
**测试问题数**: 50 个
**性能要求**: < 3 秒响应时间

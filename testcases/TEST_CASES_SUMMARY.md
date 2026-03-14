# 测试用例生成总结

## 已完成的任务

### ✅ 所有任务已完成

1. ✅ **General Intent - Word 文档**
   - 文件: `General_Insurance_Products.docx`
   - 内容: 保险产品、服务、客户支持
   - 结构: 多级标题、列表项、联系信息

2. ✅ **Finance Intent - 包含复杂表格的文档**
   - 文件: `Finance_Budget_Report.docx`
   - 内容: 年度预算报告
   - 特性: 两个复杂表格（部门预算汇总、费用类别明细）
   - 表格功能: 总计、百分比、多列数据

3. ✅ **HR Intent - Word 文档**
   - 文件: `HR_Policies.docx`
   - 内容: 人力资源政策和流程
   - 结构: 员工福利、休假政策、远程办公、绩效评估

4. ✅ **Legal Intent - Excel 文档（2个 sheet）**
   - 文件: `Legal_Compliance.xlsx`
   - Sheet 1: Regulatory Compliance（5个法规）
   - Sheet 2: Contract Templates（5个模板类型）
   - 特性: 表头格式化、列宽调整、颜色编码

5. ✅ **Intent Space 配置和测试问题 (MD 文件)**
   - 文件: `INTENT_SPACE_CONFIG.md`
   - 内容: 5个 Intent Space 完整配置
   - 关键词: 每个部门 15-20 个关键词
   - 测试问题: 50 个问题（每部门 10 个）
   - 性能要求: 所有查询必须在 3 秒内完成

6. ✅ **自动化测试脚本**
   - 文件: `auto_test.py`
   - 功能: 
     - 自动创建 5 个 Intent Space
     - 上传测试文档
     - 执行 50 个查询测试
     - 测量响应时间
     - 验证 3 秒性能要求
     - 生成详细报告（Markdown + JSON）
     - 按部门统计性能

## 生成的文件列表

### 测试文档
```
testcases/
├── General_Insurance_Products.docx     # General intent 测试文档
├── HR_Policies.docx                   # HR intent 测试文档
├── Finance_Budget_Report.docx           # Finance intent 测试文档（含复杂表格）
└── Legal_Compliance.xlsx              # Legal intent 测试文档（2 sheets）
```

### 配置文件
```
testcases/
├── INTENT_SPACE_CONFIG.md            # Intent Space 配置和测试问题
└── README.md                         # 测试用例使用说明
```

### 脚本文件
```
testcases/
├── generate_test_docs.py              # 生成测试文档的脚本
└── auto_test.py                      # 自动化测试脚本
```

## 测试场景说明

### 保险公司场景

模拟一家主要经营寿险和健康险的保险公司，涵盖：

**业务领域**:
- 寿险产品：定期寿险、终身寿险、万能寿险
- 健康险：医疗保险、处方药保险
- 财务：年度预算、费用管理、财务报告
- 人力资源：员工福利、休假政策、绩效管理
- 法务：合规要求、合同模板、监管规定
- 市场营销：营销策略、品牌管理、客户获取

**5个 Intent Space**:

1. **General** - 通用产品和服务
2. **Finance** - 财务政策和预算
3. **HR** - 人力资源政策和流程
4. **Legal** - 法律合规和合同
5. **Marketing** - 营销策略和品牌管理

## 性能测试指标

### 关键指标

| 指标 | 目标 | 测试数量 |
|--------|--------|----------|
| 总查询数 | 50 | 50 |
| 每部门查询 | 10 | 10 |
| 响应时间目标 | < 3s | 验证 |
| 成功率目标 | 100% | 测量 |
| 意图分类准确率 | > 90% | 测量 |

### 性能报告格式

自动化测试脚本生成两种报告格式：

**Markdown 报告**:
- 人类可读
- 包含总体统计
- 按部门详细性能
- 每个查询的详细结果

**JSON 报告**:
- 机器可读
- 用于自动化分析
- 包含所有测试数据
- 时间戳标记

## 使用方法

### 快速开始（自动化）

```bash
# 1. 启动后端
python backend/main.py

# 2. 运行自动化测试
python testcases/auto_test.py

# 3. 查看测试报告
# 报告将自动生成在 testcases/TEST_REPORT_*.md
```

### 手动测试

参考 `testcases/README.md` 获取详细的手动测试步骤。

## 测试检查清单

### 预测试
- [ ] 后端服务已启动
- [ ] 前端服务已启动（可选）
- [ ] 测试文档已准备
- [ ] Intent Space 配置已准备

### 执行测试
- [ ] 创建所有 5 个 Intent Spaces
- [ ] 上传所有 4 个测试文档
- [ ] 执行 50 个查询测试
- [ ] 记录每个查询的响应时间
- [ ] 验证所有查询在 3 秒内完成

### 测试后
- [ ] 生成性能报告
- [ ] 分析响应时间数据
- [ ] 识别性能瓶颈
- [ ] 记录任何失败或错误
- [ ] 必要时优化系统

## 预期结果

### 成功标准
- ✅ 所有 5 个 Intent Space 创建成功
- ✅ 所有 4 个文档上传成功
- ✅ 所有 50 个查询返回有效响应
- ✅ 所有响应在 3 秒内完成
- ✅ 意图分类准确率 > 90%
- ✅ 成功率 = 100%

### 失败情况处理
如果测试失败：
1. 检查后端日志
2. 验证 API 端点正常
3. 检查文档处理状态
4. 验证向量索引正确加载
5. 检查 DashScope API 状态

## 文档生成脚本

### regenerate_test_docs.py

如需重新生成所有测试文档：
```bash
python testcases/generate_test_docs.py
```

这将重新创建：
- `General_Insurance_Products.docx`
- `HR_Policies.docx`
- `Finance_Budget_Report.docx`
- `Legal_Compliance.xlsx`

---

**生成日期**: 2025-03-14
**状态**: ✅ 所有任务已完成
**测试文档**: 4 个
**配置文件**: 2 个
**测试脚本**: 2 个
**测试问题**: 50 个

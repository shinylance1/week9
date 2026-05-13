# RAGFlow + FastGPT 数字客户智能体总体设计方案

## 1. 建设目标

建设一个可内网自主部署的数字客户智能体，用于回答客户经理提出的「客户 XXX 的风险营销建议是什么」类问题。智能体应基于客户数据 API 返回的行业、业务数据、量化画像、司法数据、征信数据，结合 RAGFlow 知识库中的行业策略、风控政策、营销规则、合规话术，输出带引用依据的行业化风险营销建议。

## 2. 适用场景

典型问题包括：

- 客户 A 当前是否适合营销流动资金贷款？
- 客户 B 属于夕阳行业且风险等级较差，应如何维护？
- 客户 C 司法涉诉较多但结算流水稳定，应该推荐哪些低风险产品？
- 客户 D 行业处于上升周期，但征信短贷增长较快，是否可以审慎增量？

## 3. 总体架构

```text
客户经理 / CRM / 企微 / 钉钉 / 飞书
        ↓
      FastGPT
        ├─ 提取 customer_id / customer_name
        ├─ 调用适配器服务
        ├─ 组织最终 Prompt
        ├─ 调用大模型生成建议
        └─ 展示引用与行动建议

      适配器服务
        ├─ 调客户数据 API
        ├─ 校验行业字段
        ├─ 生成 RAG 检索 query
        ├─ 调 RAGFlow 检索知识库
        ├─ 标准化引用元数据
        └─ 返回结构化上下文

      RAGFlow
        ├─ 行业策略库
        ├─ 风控政策库
        ├─ 营销产品库
        ├─ 合规话术库
        ├─ 司法风险规则库
        └─ 征信解读库

      业务系统
        ├─ CRM / 客户主数据
        ├─ 业务数据
        ├─ 量化画像
        ├─ 司法数据
        ├─ 征信数据
        ├─ 风控评分
        └─ 营销产品目录
```

## 4. 组件职责

### 4.1 FastGPT

FastGPT 作为客户经理端智能体入口，负责：

- 接收客户经理问题；
- 提取客户号、客户名称等参数；
- 通过 HTTP 节点调用适配器服务；
- 将适配器返回的客户画像、风险标签、营销标签、RAGFlow 引用片段组装为最终 Prompt；
- 调用大模型输出最终建议；
- 展示引用来源，方便客户经理和审计人员追溯。

### 4.2 RAGFlow

RAGFlow 负责知识库和复杂文档检索，适合处理：

- 行业研究报告；
- 授信政策 PDF；
- 营销产品手册；
- 合规话术；
- 司法风险规则；
- 征信解读手册；
- 历史案例和风险暴露案例。

### 4.3 适配器服务

适配器服务是推荐增加的一层，主要解决三类问题：

1. 避免在 FastGPT 流程中堆积过多 HTTP 细节；
2. 统一客户数据 API 和 RAGFlow API 的返回格式；
3. 对行业缺失、知识库无依据、引用元数据不完整等情况做兜底处理。

## 5. 数据流

```text
1. 客户经理提问：客户 XXX 的风险营销建议？
2. FastGPT 提取客户号或客户名称。
3. FastGPT 调用适配器：POST /api/v1/customer-risk-context。
4. 适配器调用客户数据 API，获得行业、业务、司法、征信、画像数据。
5. 适配器校验行业字段，行业缺失则返回不可生成行业化建议。
6. 适配器基于行业、风险标签、营销标签生成多路检索 query。
7. 适配器调用 RAGFlow /api/v1/retrieval 检索知识库。
8. 适配器把检索片段、分数、文档名、页码、章节等标准化返回 FastGPT。
9. FastGPT 调用 LLM 生成最终风险营销建议。
10. 客户经理查看结论、营销建议、禁止动作、行动清单和引用依据。
```

## 6. 知识库规划

| 知识库 | 内容 | 检索条件 |
| --- | --- | --- |
| 行业策略库 | 行业周期、行业特征、夕阳/朝阳判断、区域产业特点 | `industry_code`、`industry_name`、`industry_tags` |
| 风控政策库 | 准入、授信、压降、担保、贸易背景、贷后预警规则 | `risk_level`、`risk_tags`、`credit_tags`、`judicial_tags` |
| 营销产品库 | 结算、票据、供应链金融、现金管理、代发、国际业务 | `marketing_tags`、`industry_name`、`risk_level` |
| 合规话术库 | 禁止承诺、风险提示、审批提示、客户沟通话术 | `risk_level`、`product_tags` |
| 历史案例库 | 成功营销案例、风险暴露案例、行业案例 | `industry_name`、`risk_tags` |

## 7. 客户数据 API 返回规范

```json
{
  "customer_id": "CUST_10086",
  "customer_name": "华东XX纺织有限公司",
  "basic_info": {
    "industry_code": "C17",
    "industry_name": "纺织业",
    "industry_tags": ["传统制造业", "出口敏感", "利润率偏薄", "应收账款占比较高"],
    "region": "浙江绍兴",
    "enterprise_scale": "中型企业"
  },
  "business_data": {
    "settlement_flow_12m": 190000000,
    "deposit_avg_6m": 4200000,
    "credit_balance": 35000000,
    "repayment_status": "normal"
  },
  "quant_profile": {
    "risk_level": "medium",
    "customer_value_score": 78,
    "risk_score": 72,
    "marketing_potential": "medium_high"
  },
  "judicial_data": {
    "lawsuit_count_24m": 3,
    "enforcement_count": 0,
    "dishonest_count": 0,
    "case_types": ["买卖合同纠纷", "服务合同纠纷"]
  },
  "credit_data": {
    "overdue_24m": 0,
    "external_guarantee_amount": 18000000,
    "credit_inquiry_6m": 4
  },
  "risk_tags": ["对外担保偏高", "存在涉诉记录", "无逾期", "结算流水稳定"],
  "marketing_tags": ["结算提升", "票据池", "供应链金融", "现金管理", "代发工资"]
}
```

## 8. FastGPT 流程设计

建议流程节点如下：

1. 用户输入节点：客户经理输入自然语言问题；
2. 参数提取节点：提取 `customer_id` 或 `customer_name`；
3. HTTP 节点：调用适配器 `/api/v1/customer-risk-context`；
4. 条件判断节点：如果 `status=missing_industry` 或 `status=no_evidence`，走兜底回复；
5. AI 对话节点：根据客户数据和引用片段生成最终建议；
6. 输出节点：展示结论、风险原因、营销建议、行动清单、合规话术、引用依据。

## 9. 最终输出结构

建议 FastGPT 最终输出包含：

```json
{
  "customer_name": "华东XX纺织有限公司",
  "industry": "纺织业",
  "risk_level": "medium",
  "risk_conclusion": "维持合作，审慎增量",
  "marketing_strategy": "优先结算和贸易背景类产品，控制纯信用敞口",
  "risk_reasons": [],
  "recommended_products": [],
  "not_recommended_products": [],
  "relationship_manager_actions": [],
  "compliance_script": "",
  "manual_review_required": true,
  "citations": []
}
```

## 10. 关键控制点

- 不允许模型自行识别客户行业；
- 行业字段为空时，不生成行业化建议；
- 每个风险结论至少绑定一条引用或明确标注依据不足；
- 高风险客户不输出激进营销建议；
- 禁止承诺授信额度、审批结果、收益率或营销成功率；
- 所有输入、检索结果、最终输出和模型版本必须落审计日志。

## 11. 参考链接

- FastGPT Docker Compose 部署文档：https://doc.fastgpt.io/en/docs/self-host/deploy/docker
- FastGPT 环境变量文档：https://doc.fastgpt.io/en/self-host/config/env
- FastGPT 引用分块阅读器文档：https://doc.fastgpt.cn/zh-CN/introduction/guide/DialogBoxes/quoteList
- RAGFlow HTTP API 文档：https://ragflow.com.cn/docs/http_api_reference
- RAGFlow Python API 文档：https://ragflow.docs-hub.com/docs/dev/python_api_reference/

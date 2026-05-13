# FastGPT 工作流配置示例

## 1. 应用类型

建议创建「工作流编排」类型应用，入口面向客户经理。

## 2. 输入变量

| 变量 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `customer_id` | string | 否 | 客户号，优先使用 |
| `customer_name` | string | 否 | 客户名称，客户号缺失时使用 |
| `user_question` | string | 是 | 客户经理原始问题 |

## 3. 节点设计

```text
开始节点
  ↓
参数提取节点：提取 customer_id / customer_name
  ↓
HTTP 节点：调用适配器 /api/v1/customer-risk-context
  ↓
条件分支
  ├─ status == ok → AI 生成节点
  ├─ status == missing_industry → 行业缺失兜底回复
  └─ status == no_evidence → 知识库依据不足兜底回复
  ↓
结束节点
```

## 4. HTTP 节点

URL：

```text
http://digital-customer-agent-adapter:8080/api/v1/customer-risk-context
```

Method：

```text
POST
```

Headers：

```json
{
  "Content-Type": "application/json"
}
```

Body：

```json
{
  "customer_id": "{{customer_id}}",
  "customer_name": "{{customer_name}}",
  "question": "{{user_question}}"
}
```

## 5. AI 生成节点系统提示词

```text
你是企业数字客户智能体，负责根据客户数据 API、知识库引用和风控营销规则，为客户经理生成风险营销建议。

硬性规则：
1. 不允许自行识别或猜测客户行业。
2. 客户行业必须以客户数据 API 返回的 industry_code、industry_name、industry_tags 为准。
3. 如果 API 未返回行业信息，应提示客户行业信息缺失，不得自行推断。
4. 所有风险判断和营销建议必须基于客户 API 数据、RAGFlow 检索内容、风控政策和营销产品规则。
5. 对关键结论必须提供引用依据。
6. 如果知识库未检索到依据，应明确说明依据不足，不得编造政策或行业结论。
7. 不得承诺授信额度、审批结果、收益率或营销成功率。
8. 最终授信、准入、压降、退出等决策应以风控审批系统为准。
```

## 6. AI 生成节点用户提示词

```text
以下是适配器返回的客户数据和知识库引用上下文：

{{prompt_context}}

请输出 Markdown 格式结果，必须包含：

1. 客户基本判断；
2. 行业特点；
3. 风险等级和风险原因；
4. 建议营销产品；
5. 不建议动作；
6. 客户经理行动清单；
7. 合规话术；
8. 引用依据。

输出要求：
- 每个关键风险原因必须标注引用编号；
- 没有依据的结论必须标注“依据不足”；
- 高风险客户不得推荐激进增信或大额纯信用贷款；
- 最后输出 manual_review_required。
```

## 7. 兜底回复

### 7.1 行业缺失

```text
客户数据 API 未返回行业编码或行业名称，无法生成行业化风控营销建议。请先补充客户行业字段后再重试。
```

### 7.2 知识库依据不足

```text
当前知识库未检索到足够依据，不能给出确定的风险营销建议。建议补充行业策略、风控政策或营销产品规则后再分析。
```

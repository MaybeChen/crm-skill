# Swagger 2.0 节点映射

## 先判断节点角色

以一个 `post` operation 为单位，从外向内区分：

| YAML 节点 | 角色 | 默认处理 |
|---|---|---|
| `info.description` | 整个服务 | 文档无命中时根据服务上下文推断 |
| `paths.<path>.<method>.description` | 方法 | 描述该方法执行的业务动作；不要使用请求/响应体模板 |
| `parameters[]` 且 `in: body` 的 `description` | 完整请求体 | 文档无命中时使用 request 固定模板 |
| `responses.<code>.description` | 完整响应 | 文档无命中时使用 response 固定模板 |
| body/response schema 的顶层 property | 消息包装字段 | 作为字段描述，不使用 request/response 固定模板 |
| `definitions.<name>` | 复用业务对象 | 仅用户范围包含对象描述时补充 |
| `definitions.<name>.properties.<field>` | 业务字段 | 文档无命中时结合完整上下文推断 |

## 避免重复描述

请求链路可能同时出现 body parameter、消息包装字段和其引用的业务 definition；响应链路也可能同时出现 response、消息包装字段和 definition。固定模板只写在 body parameter 或 status response 的标准 `description`，不复制到包装字段或 definition。已有非空 `description` 时保留文档内容，不用回退模板覆盖。

## 描述键

- 所有层级统一使用标准 `description`。
- 已有空 `description` 时补值；目标范围内的节点完全没有 `description` 时新增该键。
- `x-description-zh` 不属于本任务的描述目标：保持原值，不因其为空而报告缺失，也不把生成内容写入该键。
- 同一节点同时有 `description` 与 `x-description-zh` 时，只判断和补充 `description`。

## 对示例结构的具体判断

- `post_Test` 的业务方法名为 `Test`：先去掉 operationId 的 `post_` 前缀。
- `parameters[].description` 表示完整请求体；为空且文档未命中时使用 `The request params of Test`。
- `responses.200.description` 表示完整响应；为空且文档未命中时使用 `The response params of Test`。
- schema 顶层的 `TestReqMsg` / `TestRspMsg` property 是包装字段，不重复使用固定模板。
- `x-description-zh: ""` 保持不变，不计入待补充数量。
- `sender`、`content`、`sendOptions` 等纯 `$ref` property 仍是字段；没有 `description` 时应进入缺失项清单。
- 数组 property 与 `items` 是不同节点；仅在目标范围要求数组元素描述时为 `items` 添加独立的 `description`。

# Swagger 2.0 节点映射

## 先判断节点角色

以一个 `post` operation 为单位，从外向内区分：

| YAML 节点 | 角色 | 默认处理 |
|---|---|---|
| `info.description` | 整个服务 | 文档无命中时根据服务上下文推断 |
| `paths.<path>.<method>.description` | 方法 | 描述该方法执行的业务动作；不要使用请求/响应体模板 |
| `parameters[]` 且 `in: body` | body parameter | 已有非空通用描述时通常保留 |
| body schema 的顶层 property | 请求消息包装字段 | 文档无命中时使用 request 固定模板 |
| `responses.<code>.description` | HTTP/业务响应状态 | 已有非空描述时保留；不要替换为 response params 模板 |
| response schema 的顶层 property | 响应消息包装字段 | 文档无命中时使用 response 固定模板 |
| `definitions.<name>` | 复用业务对象 | 仅用户范围包含对象描述时补充 |
| `definitions.<name>.properties.<field>` | 业务字段 | 文档无命中时结合完整上下文推断 |

## 避免重复描述

请求链路可能同时出现 body parameter、消息包装字段和其引用的业务 definition；响应链路也可能同时出现 response、消息包装字段和 definition。固定 request/response params 模板只写一次。优先级为：

1. 遵循同一 YAML 中已经形成的约定；
2. 没有约定时写在 schema 的顶层消息包装字段；
3. 若没有包装字段，才写在直接承载完整 body schema 的描述扩展键。

不要覆盖已经非空的 `parameters[].description` 或 `responses.<code>.description`。

## 选择描述键

- 服务和 operation 优先使用标准 `description`。
- 字段已有空 `x-description-zh` 时补该键，不额外新增 `description`。
- 字段已有空 `description` 时补该键；若同一字段的 `x-description-zh` 也为空，两个键分别按其项目约定处理，不把英文内容无条件复制到中文键。
- 字段完全没有描述键时，观察同一父 schema 和全文件的字段惯例。本类文件以 `x-description-zh` 为主时新增 `x-description-zh`。
- 固定 request/response params 模板是例外：即使目标键为 `x-description-zh`，仍写规定的英文模板。

## 对示例结构的具体判断

- `post_SendNotification` 是 operationId，可用于请求/响应模板中的方法名。
- `reqBody.description` 已经非空，不应覆盖；它不等于 operation description。
- `SendNotificationReqMsg` 是请求消息包装字段，适合 `The request params of post_SendNotification`。
- HTTP `200.description` 已经非空，不应覆盖。
- `SendNotificationRspMsg` 是响应消息包装字段，适合 `The response params of post_SendNotification`。
- `sender`、`content`、`sendOptions` 等纯 `$ref` property 仍是字段；即使没有现成描述键，也应进入缺失项清单。
- `attachments.items.x-description-zh` 描述数组元素，而 `attachments.x-description-zh` 描述整个附件数组，两者不能互相替代。

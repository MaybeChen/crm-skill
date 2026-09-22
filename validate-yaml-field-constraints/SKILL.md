---
name: validate-yaml-field-constraints
description: Validate and minimally correct field constraints in YAML API or service schemas against supplied long-form specifications, including simple-field type, format, maxLength, and enum values and complex-type required child lists. Use when reconciling Swagger/OpenAPI or similar YAML with Word, PDF, Excel, HTML, or text documentation where complex types are primarily connected through $ref, service-specific and common sections must be searched, exact nested field paths must be disambiguated, and every change must have an explicit documentary source.
---

# Validate YAML Field Constraints

依据文档校验 YAML 字段约束，只修改有明确文档证据且路径完全匹配的值。文档无法确定时保留 YAML 原值。绝对禁止猜测、补造或根据 YAML 自身内容反推文档结论。

## 工作边界

- 简单类型字段只校验 `type`、`format`、`maxLength` 和 `enum`。
- 复杂类型只校验其直接子字段组成的 `required` 集合。
- 除目标范围内的 `type`、`format`、`maxLength`、`enum`、对象级 `required` 外，不修改字段名、路径、描述、示例、默认值、引用或其他契约内容，除非用户另有明确要求。
- 不根据字段名、业务常识、描述性文字中的可能含义、示例值、现有 YAML 值、编程语言习惯或历史检查结果猜测类型、格式、长度、枚举或必填性。YAML 现值只能作为待校验值，不能作为文档证据。
- 保留 YAML 的格式、注释、引号、键顺序、换行符和编码；优先做最小文本编辑。
- 除非用户明确要求原地修改，否则先创建不覆盖已有文件的工作副本，并只编辑副本。

## 流程

### 1. 盘点 YAML 并解析引用图

1. 识别服务信息，例如 `info.title`、服务名、tags、paths、operationId、schema 名和命名空间。
2. 为每个待校验字段记录**声明路径**，路径必须包含所有 YAML 层级，并区分 schema、请求/响应、数组元素和嵌套对象。示例：
   - `definitions.CreateOrder.properties.customer.properties.id`
   - `paths./orders.post.parameters.body.schema.properties.customer.properties.id`
   - `definitions.Order.properties.lines.items.properties.id`
3. 从所有 schema 入口建立引用图。入口至少包括 `definitions`、body parameter 的 `schema`、response 的 `schema`、内联对象以及数组的 `items`：
   - 对属性节点的 `$ref: "#/definitions/X"`，将**使用路径**记为当前属性路径，将**声明路径**记为 `definitions.X`。
   - 对数组 `items.$ref`，先在使用路径加入 `items`，再跳转到对应 definition。
   - 递归解析 definition 内的 `$ref`，同时维护已访问引用集合；遇到循环引用时停止继续展开，但保留引用边，禁止因循环而复制或遗漏定义。
   - 只解析本文件中能够精确定位的 JSON Pointer。外部引用、损坏引用或无法解析的引用保持不变并报告。
4. 为每个可达字段同时记录“使用路径 → `$ref` 链 → 声明路径”。例如：
   `paths./SendNotification.post.parameters[0].schema.properties.SendNotificationReqMsg.properties.sendNotificationRequest → #/definitions/SendNotificationRequest → definitions.SendNotificationRequest.properties.sender → #/definitions/Sender → definitions.Sender.properties.email`。
5. 将节点分类：
   - 简单字段：声明节点为标量，校验 `type`、`format`、`maxLength` 和 `enum`。
   - 复杂类型：声明节点包含 `properties`，或经 `$ref` 指向包含 `properties` 的对象；在真正声明这些子字段的对象节点校验 `required`。
   - 数组：数组节点自身与 `items` 分开处理。数组元素经 `$ref` 指向对象时，对象约束写在目标 definition；`items` 为简单类型时，只校验 `items` 节点上有文档证据的简单字段约束。
6. `$ref` 的使用节点与目标 definition 不得合并成同一声明路径。字段约束应修改在实际声明该字段的节点；不得把目标 definition 的 `type`、`format`、`maxLength`、`enum` 或 `required` 复制到 `$ref` 使用节点。
7. 同一 definition 可被多个接口引用。只有当文档证据明确适用于该公共 definition，或所有使用语境的说明一致时，才修改该 definition；若不同使用语境给出冲突约束，保持 definition 不变并报告冲突，禁止任选一个值。

### 2. 在长文档中定位证据

先用目录、标题、书签、工作表名和全文搜索缩小范围，不要线性通读整份文档。按以下顺序检索：

1. 与 YAML 服务信息对应的服务章节。
2. 对应 path、operationId、请求/响应对象或 schema 的章节。
3. 文档明确标为公共、通用、基础对象或数据字典的章节。
4. 精确字段名，并结合使用路径、完整 `$ref` 链、声明路径和请求/响应方向消歧。

服务专属章节与公共章节冲突时，不能直接使用服务专属值改写被其他接口复用的公共 definition；仅当修改范围是服务私有声明节点时才采用更具体的说明。其他冲突保持不变并报告。文档中的字段只有在完整层级、所属对象、接口方向和语境均与“使用路径 + `$ref` 链 + 声明路径”一致时才算命中。孤立的同名字段不是证据。

为每项建立证据记录：使用路径、`$ref` 链、声明路径、YAML 现值、文档值、文档位置、匹配依据、决定。低置信度、冲突或只有同名匹配的项目保持不变。

### 3. 校验简单字段的 `type`

只在文档明确给出类型且字段路径完全匹配时，按下表规范化：

| 文档类型（忽略大小写） | YAML `type` |
|---|---|
| `string`, `varchar`, `varchar2`, `char`, `text` | `string` |
| `datetime`, `timestamp`, `date` | `dateTime` |
| `boolean`, `bool` | `boolean` |
| `number`, `numeric`, `money`, `bigdecimal` | `decimal` |
| `integer`, `int`, `smallint`, `tinyint`, `byte`, `short` | `int` |
| `long`, `bigint` | `long` |
| `decimal` | `decimal` |
| `float`, `real` | `float` |
| `double` | `double` |

严格遵守以下限制：

- `integer` 仅是输入关键字，最终输出禁止出现 `type: integer`。
- 文档类型为 `number` 时必须输出 `decimal`。不得因字段名、业务语义、示例值、历史检查结果或语言习惯改成 `int`、`long`、`float` 或 `double`。
- 先去除类型文本首尾空白，再对上表中的完整类型关键字做不区分大小写的匹配。对于 `string(N)`，将基础类型识别为 `string`，并按下一节单独处理长度。
- 带有未定义修饰词、联合类型或无法映射的类型不做改动；不要自行扩展映射表。

### 4. 校验简单字段的 `maxLength`

仅从文档的字段长度描述或文档类型中的有效 `string(N)` 得出长度：

- `string` 关键字忽略大小写。
- 关键字与左括号之间、括号内部允许任意空白。
- 等价识别正则为 `^string\s*\(\s*(\d+)\s*\)$`。
- 捕获值必须是大于 `0` 的十进制整数，写入 YAML 时使用整数值。
- `string(20)`、`String (20)`、`STRING ( 20 )` 均得到 `maxLength: 20`。
- `string(0)`、`string(-1)`、`string(10.5)`、`string(abc)` 以及没有明确长度的 `string` 均不产生长度证据。
- 未识别到有效长度时，保留现有 `maxLength`，既不删除也不改写。

文档若在独立的“长度”列明确给出大于 `0` 的十进制整数，也可作为 `maxLength` 证据。不要从示例值字符数、数据库展示宽度或其他字段的长度推断。

### 5. 校验简单字段的 `format`

- 只有文档为完整匹配字段明确提供格式值时，才新增、替换或删除 `format`。格式值必须忠实采用文档值；本 skill 不提供 `format` 推断或转换表。
- 文档仅给出 `datetime`、`date`、`timestamp` 等**类型关键字**时，只按类型映射表处理 `type`，不得自动生成 `format: date-time`、`format: date` 或其他格式。
- `type: number`、字段名含 `id`、整数示例、现有 `format: int64` 等均不能证明文档格式为 `int64`。同理，email、URL、UUID 等业务含义或示例不能证明对应 `format`。
- 文档未明确格式、格式描述含糊、或只有 YAML 现值而无外部文档来源时，保留现有 `format` 不变。

### 6. 校验简单字段的 `enum`

- 只有文档明确声明字段的完整允许值集合时，才新增、替换或删除 `enum`。逐项保留文档中的值、大小写和标量类型；不要把数字字符串改为数字，也不要自行排序、翻译或规范化。
- 只有在文档明确说明列出的值是**全部可选值**时，才可用该集合替换现有 `enum`。若文档使用“例如”“包括但不限于”等非穷举措辞，或仅能确认部分值，则保持整个现有 `enum` 不变并报告，不得只追加已知值。
- 值的说明文字不是枚举值。例如文档明确列出代码 `101`（SMS）和 `6`（email）时，枚举只包含文档声明的代码，不包含 `SMS`、`email` 或自行拆分出的其他文本。
- 不得从 YAML 现有 `description`、`example`、`default`、条件分支、其他同名字段或现有 `enum` 反推出文档枚举。外部文档正文只有在明确声明完整允许值集合时才是有效来源。空集合或删除枚举也必须有文档明确说明该字段没有枚举限制。

### 7. 校验复杂类型的 `required`

1. 沿 `$ref` 到达实际声明复杂对象的节点，在文档对应对象中收集被明确标记为必填的**直接子字段**。
2. 使用 YAML 中子字段的精确键名组成 `required` 数组；不得使用显示名、别名或点路径。
3. 仅当文档能确定该复杂类型全部直接子字段的必填状态时，才将 `required` 校正为完整集合，包括删除文档明确为非必填的旧成员。
4. 若文档只明确说明部分字段必填、但无法判断其余字段，则只能安全地补充已确认的必填项，不得删除现有成员。
5. 文档明确确认没有直接必填子字段时，遵循目标规范现有风格删除 `required` 或设为空数组；不要把空集合放到某个子字段上。
6. 嵌套对象分别处理：父对象的 `required` 只包含其直接子字段；孙字段应写入定义孙字段的嵌套对象的 `required`。
7. 不要将 `required: true/false` 写在属性节点上，也不要把请求参数层的 `required` 与 schema 对象的 `required` 混淆。

### 8. 编辑与验证

1. 先完成证据表，再批量做最小编辑；不要边搜索边凭印象修改。
2. 使用可用的 YAML 解析器确认结果可解析；若是 OpenAPI，再使用可用的 OpenAPI 校验器。
3. 检查 diff，确认只发生有证据支持的 `type`、`format`、`maxLength`、`enum` 和对象级 `required` 变化，且约束写在正确的声明节点。
4. 搜索最终文件中的 `type: integer`（包括等价的空白和引号形式），确保没有遗留；若该值不在本次证据覆盖范围内，将其报告为待确认，不要在无文档依据时擅自映射。
5. 对每个修改项反向核对使用路径、完整 `$ref` 链、声明路径和文档位置，重点复核同名字段、嵌套对象、数组元素、复用 definition 和请求/响应重名对象。
6. 扫描 `$ref`，确认所有本地引用都可解析，并检查没有把 definition 约束复制到引用节点。无法解析的引用必须进入未修改清单。

## 交付

交付修改后的 YAML 工作副本，并报告：

- `type`、`format`、`maxLength`、`enum`、`required` 各修改多少项。
- 每项修改的使用路径、`$ref` 链、声明路径、旧值、新值和文档位置。
- 因无匹配、路径歧义、引用无法解析、无映射、无有效长度、枚举集合不完整、必填集合不完整或来源冲突而保持不变的项目。
- YAML/OpenAPI 解析、禁止类型扫描和 diff 检查的命令与结果。

不要声称未修改项“正确”；只能说明文档证据不足，因此按规则保持不变。

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

### 1. 从方法入口构建业务字段路径

1. 识别服务信息以及 `paths` 下的每个方法。为每个方法单独记录 `path + HTTP method + operationId`，不得混合不同方法的字段。
2. 从方法的请求体和响应体分别开始遍历：
   - 请求体根固定记为 `request`。
   - 响应体根固定记为 `response`；HTTP 状态码作为方法上下文单独记录，不作为字段路径的一段。
   - 根以下只追加实际业务字段名。`schema`、`properties`、`items`、`definitions`、definition 名、请求/响应消息类型名和 `$ref` 均不是业务字段，禁止出现在字段路径中。
3. 先识别并跳过请求体或响应体最外层的**消息类型包装节点**。当根 schema 下的节点只是承载一个复杂消息对象、其名称表示请求/响应消息类型（例如示例中的 `SendNotificationReqMsg`、`SendNotificationRspMsg`），而真正业务字段位于其 `properties` 内时，该名称是类型名而不是字段名，不得加入业务字段路径。不得仅凭 `ReqMsg`/`RspMsg` 后缀机械判断；应同时依据根层级、复杂对象结构以及文档中的消息/对象定义确认。若无法确认它是包装类型名，则保持该路径候选未决，不要擅自跳过或修改相关字段。
4. 遇到 `$ref: "#/definitions/X"` 时透明跳转到 `X` 并继续追加其中的字段名。遇到数组时保留数组字段本身的名称，随后透明进入 `items`；不要向路径添加 `items` 或 `[]`。
5. 递归展开 definition 中的 `$ref`，同时维护当前遍历链上的引用集合。遇到循环引用时停止该分支并报告；遇到外部引用、损坏引用或无法解析的 JSON Pointer 时保持相关字段不变并报告。
6. 为每个可达字段生成**业务字段路径**。以示例中的 `post_SendNotification` 为例，`SendNotificationReqMsg` 和 `SendNotificationRspMsg` 是消息类型名，必须跳过：
   - `request.requestHeader.version`
   - `request.sendNotificationRequest.sender.email`
   - `request.sendNotificationRequest.receiver.email`
   - `response.resultHeader.resultCode`
   这些路径描述字段在某个方法的请求体或响应体中的唯一业务位置，绝不能写成 `definitions.Sender.properties.email` 或 `paths....schema.properties...`。
7. 业务字段路径只用于识别和消歧，不等于 YAML 的物理位置。另行记录内部**编辑位置**（例如目标 definition 的 JSON Pointer），仅用于准确修改文件；证据匹配和交付报告以“方法上下文 + 业务字段路径”为主。若约束属于简单数组元素，额外记录“数组元素”节点角色来定位 `items`，但仍不把 `items` 写进业务字段路径。
8. 将路径对应的节点分类：
   - 简单字段：最终节点为标量，校验 `type`、`format`、`maxLength` 和 `enum`。
   - 复杂类型：最终节点包含 `properties`，或经 `$ref` 指向对象；在实际定义其直接子字段的对象节点校验 `required`。
   - 数组：数组字段自身与其元素字段分开校验。数组元素经 `$ref` 指向对象时，继续生成后代业务字段路径；`items` 为简单类型时，简单类型约束仍写在 `items` 的实际编辑位置。
9. 同一 definition 被多个方法、方向或父字段引用时，为每个使用位置生成各自的业务字段路径，但它们可能指向同一个编辑位置。只有文档证据明确适用于所有这些使用位置且约束一致时，才修改共享 definition；任一使用语境冲突或无法确认时保持不变并报告。

### 2. 在长文档中定位证据

先用目录、标题、书签、工作表名和全文搜索缩小范围，不要线性通读整份文档。按以下顺序检索：

1. 与 YAML 服务信息对应的服务章节。
2. 对应 path、operationId、请求/响应对象或 schema 的章节。
3. 文档明确标为公共、通用、基础对象或数据字典的章节。
4. 精确字段名，并结合方法上下文、请求/响应方向、父子字段层级和对象表格消歧。

文档不要求逐字出现 `request.a.b.c` 形式。允许根据章节所属方法、请求/响应表、对象标题、表格层级、父字段和字段名，推断文档行与业务字段路径的对应关系；这里允许推断的是**字段对应关系**，绝不允许推断 `type`、`format`、`maxLength`、`enum` 或 `required` 的值。只有对应关系唯一且文档明确写出待校验值时才能修改。

服务专属章节与公共章节冲突时，不能直接使用服务专属值改写被其他接口复用的 definition；仅当编辑位置不共享时才采用更具体的说明。其他冲突保持不变并报告。孤立的同名字段、只有字段名而无法确认父级或方向的记录，以及存在多个合理对应路径的记录都不是充分证据。

为每项建立证据记录：方法上下文、业务字段路径、内部编辑位置、YAML 现值、文档值、文档位置、对应依据、决定。低置信度、冲突或无法唯一对应的项目保持不变。

### 3. 校验简单字段的 `type`

只在文档明确给出类型且文档记录能唯一对应到业务字段路径时，按下表规范化：

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

1. 根据业务字段路径识别复杂对象，再沿 `$ref` 到达实际定义该对象的节点；在文档对应对象中收集被明确标记为必填的**直接子字段**。
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
5. 对每个修改项反向核对方法上下文、业务字段路径、内部编辑位置和文档位置，重点复核同名字段、嵌套对象、数组元素、复用 definition 和请求/响应重名对象。
6. 扫描 `$ref`，确认所有本地引用都可解析，并检查没有把 definition 约束复制到引用节点。无法解析的引用必须进入未修改清单。

## 交付

交付修改后的 YAML 工作副本，并报告：

- `type`、`format`、`maxLength`、`enum`、`required` 各修改多少项。
- 每项修改的方法上下文、`request...` 或 `response...` 业务字段路径、内部编辑位置、旧值、新值和文档位置。
- 因无匹配、路径歧义、引用无法解析、无映射、无有效长度、枚举集合不完整、必填集合不完整或来源冲突而保持不变的项目。
- YAML/OpenAPI 解析、禁止类型扫描和 diff 检查的命令与结果。

不要声称未修改项“正确”；只能说明文档证据不足，因此按规则保持不变。

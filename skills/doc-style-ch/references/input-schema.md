# 输入 JSON 结构

最小输入：

```json
{
  "title": "文档标题",
  "sections": [
    {
      "title": "第一节",
      "blocks": [
        {"type": "paragraph", "text": "正文。"}
      ]
    }
  ]
}
```

顶层字段：

- `title`：必填字符串。
- `subtitle`：可选字符串。
- `kicker`：可选短标签。
- `meta`：可选字符串数组。
- `lead`：可选导语。
- `footer`：可选页尾文字。
- `sections`：必填数组，至少一节。

章节字段：

- `title`：必填字符串。
- `eyebrow`：可选短标签。
- `blocks`：必填内容块数组。

内容块：

- `paragraph`：`{"type":"paragraph","text":"..."}`
- `bullets`：`{"type":"bullets","items":["...","..."]}`
- `steps`：`{"type":"steps","items":["...","..."]}`
- `quote`：`{"type":"quote","text":"...","cite":"可选出处"}`
- `callout`：`{"type":"callout","tone":"note|warning|success","title":"...","text":"..."}`
- `table`：`{"type":"table","headers":["列一"],"rows":[["值一"]]}`
- `code`：`{"type":"code","language":"python","text":"..."}`
- `divider`：`{"type":"divider"}`
- `image`：`{"type":"image","src":"images/example.png","alt":"替代文本","caption":"可选说明"}`

文本默认按纯文本转义，支持四种行内标记：`**粗体**`、`*强调*`、`` `代码` ``、`[链接文字](https://example.com)`。链接只接受 `http`、`https`、`mailto` 或相对路径。

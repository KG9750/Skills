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
- `kicker`：可选短标签，省略时默认为 `DOC STYLE · CH`。
- `meta`：可选字符串数组。
- `lead`：可选导语。
- `footer`：可选页尾文字。
- `sections`：必填数组，至少一节。

可选字段可以省略；一旦出现，必须符合所列类型，不接受 JSON `null`。所有字符串均不接受 NUL 字符；URL 和图片路径不得包含换行。

章节字段：

- `title`：必填字符串。
- `eyebrow`：可选短标签，省略时默认为 `SECTION`。
- `blocks`：必填非空内容块数组，至少一个内容块。

内容块：

- `paragraph`：`{"type":"paragraph","text":"..."}`
- `bullets`：`{"type":"bullets","items":["...","..."]}`
- `steps`：`{"type":"steps","items":["...","..."]}`
- `quote`：`{"type":"quote","text":"...","cite":"可选出处"}`
- `callout`：`{"type":"callout","tone":"note|warning|success","title":"...","text":"..."}`；`tone` 可省略并默认为 `note`，`title` 可省略并默认为“提示”。
- `table`：`{"type":"table","headers":["列一"],"rows":[["值一"]]}`；`headers` 和 `rows` 都必须是非空数组，每行列数必须与表头一致。
- `code`：`{"type":"code","language":"python","text":"..."}`；`language` 可省略并默认为 `text`。
- `divider`：`{"type":"divider"}`
- `image`：`{"type":"image","src":"images/example.png","alt":"替代文本","caption":"可选说明"}`；`src` 只接受相对本地路径，不接受远程 URL、协议相对 URL 或根路径。

文本默认按纯文本转义，支持四种行内标记：`**粗体**`、`*强调*`、`` `代码` ``、`[链接文字](https://example.com)`；文本中的换行会转换为 `<br>`。链接只接受 `http`、`https`、`mailto` 或相对路径，不接受 `//host/path` 形式的协议相对 URL。

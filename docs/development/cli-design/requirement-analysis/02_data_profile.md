# Data Profile

## 1. Latest Workbook Shape

Observed workbook: `files/current_record_tree.xlsx`

| Property | Value |
|---|---:|
| Sheets | 1 |
| Main sheet | `Sheet1` |
| Header row | Row 1 |
| Data rows | tens of thousands |
| Columns | 10 |
| Parsed MEGA link items | hundreds of thousands |
| MEGA JSON parse errors | 0 |

## 2. Workbook Columns

| Position | Header | Required handling |
|---:|---|---|
| 1 | `声优` | Required. Store raw actor name and normalized actor mapping. |
| 2 | `配信日期` | Optional date. Store as ISO date or null. |
| 3 | `标题` | Required in current workbook. Store raw title. |
| 4 | `录入日期` | Optional date. Store as ISO date or null. |
| 5 | `备注` | Optional text. Store raw note; values often describe record count. |
| 6 | `上传标题` | Required. Store as upload title / file group display name. Not unique by itself. |
| 7 | `重复检索` | Required in current workbook. Store raw duplicate-search helper text for debugging/search. |
| 8 | `来源` | Required. Store raw source and normalized source mapping. |
| 9 | `MEGA` | Required JSON. Parse into link rows. Preserve raw JSON for audit if practical. |
| 10 | `容量` | Required display size. Store raw text and parsed bytes when possible. |

## 3. Blank Counts

Blank or null-like values observed:

| Column | Blank count |
|---|---:|
| `声优` | 0 |
| `配信日期` | 3 |
| `标题` | 0 |
| `录入日期` | 2 |
| `备注` | many |
| `上传标题` | 0 |
| `重复检索` | 0 |
| `来源` | 0 |
| `MEGA` | 0 |
| `容量` | 0 |

Implications:

- Importer must allow missing dates and notes.
- Search and display commands must render missing dates cleanly.
- Actor, title, source, upload title, MEGA, and size can be treated as required for the current xlsx contract.

## 4. Date Ranges

Observed date ranges:

| Field | Minimum | Maximum |
|---|---|---|
| `配信日期` | historical date | latest workbook date |
| `录入日期` | historical date | latest workbook date |

Implications:

- Date parsing should accept Excel date cells and date-like strings.
- Very old dates should not be rejected automatically.
- Future imports may contain dates later than the current file, so validation should focus on parseability rather than a fixed date window.

## 5. Identity And Duplicate Signals

Observed uniqueness checks:

| Field | Duplicate count |
|---|---:|
| `上传标题` | 21 |
| `MEGA` | 0 |

Implications:

- `上传标题` is not a safe unique key by itself.
- `MEGA` uniqueness is an observation, not a stable identity rule.
- Use a generated import identity and keep enough source columns for conflict review.

Recommended identity candidates:

1. Primary internal id: autoincrement `record_groups.id`.
2. Stable source key: hash of normalized `声优`, `配信日期`, `标题`, `录入日期`, `上传标题`, `来源`.
3. Link-set hash: hash of normalized active link items, used only to detect link changes.

## 6. MEGA JSON Shape

All inspected rows had the same root keys:

```json
{
  "FileNames": "[actor][date][title][entry-date]",
  "total": "<bytes>",
  "FormattedSize": "<display-size>",
  "property": [
    {
      "Link": "https://mega.nz/file/...",
      "Size": "<bytes>",
      "FormattedSize": "<display-size>",
      "Type": ".mp4"
    }
  ]
}
```

Observed root keys:

- `FileNames`
- `total`
- `FormattedSize`
- `property`

Observed link item keys:

- `Link`
- `Size`
- `FormattedSize`
- `Type`

Importer requirements:

- Parse `MEGA` as JSON.
- Require `property` to be a list for link import.
- Require each valid link item to have `Link` and integer-compatible `Size`.
- Store `Type` as the file extension/type when present.
- Store `FormattedSize` for display.
- Store JSON `FileNames` separately from workbook `上传标题` because they should normally match but are not guaranteed to remain identical.

## 7. Link Count Distribution

Observed link count per row:

| Links per row | Row count |
|---:|---:|
| 1 | uncommon |
| 2 | most common |
| 3 | common |
| 4 | common |
| 5+ | uncommon |

Implications:

- Multiple links per record group are normal.
- Download planning must sum selected links, not rely only on `容量`.
- CLI output should be compact for large link sets.

## 8. File Type Distribution

Most common link types:

| Type | Count |
|---|---:|
| `.mp4` | very common |
| `.m4a` | common |
| `.par2` | common |
| `.exe` | occasional |
| `.rar` | occasional |
| `.ts` | occasional |
| `.mp3` | rare |
| `.mkv` | rare |
| `.wav` | rare |
| `.webm` | rare |

Implications:

- `.par2` files are common and need explicit include/exclude behavior.
- Type filters should support common extensions such as `.mp4`, `.m4a`, `.rar`, `.exe`, `.ts`, `.mp3`, `.wav`.
- Some malformed or unusual types exist, so file type should be stored as raw text and normalized conservatively.

## 9. Source Distribution

Top observed sources:

| Source | Count |
|---|---:|
| `niconico` | high |
| `Withny` | high |
| `rPlay` | high |
| `Twitcasting` | medium |
| `NicoChannel` | medium |
| `Twitch` | medium |
| `X` | medium |
| `Fantia` | lower |
| `fc2Live` | lower |
| `Ci-en` | lower |

Implications:

- Source should be searchable.
- Preserve source casing for display while using normalized casing for search.

## 10. Legacy SQLite Profile

Observed database: `files/legacy_record.db`

| Table | Count |
|---|---:|
| `author` | thousands |
| `record` | hundreds of thousands |

Download status:

| Status | Count |
|---|---:|
| Downloaded (`downloaded_date != '0'`) | some |
| Undownloaded (`downloaded_date = '0'`) | most |

Other observations:

- Duplicate links in legacy `record.link`: 0
- Orphan records without author: 0
- Record date range: historical through recent source dates
- Added date range: recent import dates

Legacy migration requirements:

- Preserve `record_id` as `legacy_record_id` or a migration mapping.
- Preserve `author_id` as `legacy_author_id`.
- Preserve `downloaded_date`.
- Treat `downloaded_date = '0'` as not downloaded.
- Avoid creating duplicate active link rows when the same URL exists from xlsx import.

## 11. Legacy JSON Profile

Observed file: `files/legacy_record_tree.json`

Shape:

```json
[
  {
    "author": "...",
    "total_records": "<count>",
    "records": [
      {
        "FileNames": "...",
        "total": "<bytes>",
        "FormattedSize": "3.39 GB",
        "property": [
          {
            "Link": "https://mega.nz/file/...",
            "Size": "<bytes>",
            "FormattedSize": "3.16 GB",
            "Type": ".mp4"
          }
        ]
      }
    ]
  }
]
```

Observed count:

- Authors: hundreds

Notes:

- Some text in the inspected JSON appears mojibake compared with the current xlsx and database.
- JSON import should be retained but should not be the primary path for high-quality metadata.
- If the same links appear in the xlsx import, xlsx metadata should be treated as the better source.

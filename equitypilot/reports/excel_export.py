"""Formatted Excel workbooks (openpyxl): navy header, frozen panes, number formats, notes sheet."""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .. import config

HEADER_FILL = PatternFill("solid", fgColor="0B1F3A")
HEADER_FONT = Font(bold=True, color="FFFFFF")
THIN = Side(style="thin", color="E3E8F0")

FORMATS = {"pct": "0.0%", "x": '0.0"x"', "inr": "₹#,##0.00", "cr": "#,##0", "num": "#,##0.00", "int": "0"}


def workbook(sheets: dict[str, tuple[pd.DataFrame, dict[str, str]]], notes: list[str]) -> bytes:
    """sheets: name -> (dataframe, {column: format key}). Returns .xlsx bytes."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, (df, fmts) in sheets.items():
            sheet = name[:31]
            df.to_excel(xw, sheet_name=sheet, index=False)
            ws = xw.sheets[sheet]
            for j, col in enumerate(df.columns, start=1):
                cell = ws.cell(row=1, column=j)
                cell.fill, cell.font = HEADER_FILL, HEADER_FONT
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                fmt = FORMATS.get(fmts.get(col, ""))
                width = max([len(str(col))] + [len(str(v)) for v in df[col].head(200)]) + 2
                ws.column_dimensions[get_column_letter(j)].width = min(max(width, 9), 48)
                for i in range(2, len(df) + 2):
                    c = ws.cell(row=i, column=j)
                    c.border = Border(bottom=THIN)
                    if fmt:
                        c.number_format = fmt
            ws.freeze_panes = "B2"
            ws.row_dimensions[1].height = 30
            ws.auto_filter.ref = ws.dimensions
        meta = pd.DataFrame({"Notes": [f"{config.APP_NAME} export - {datetime.now():%d %b %Y %H:%M}"] + notes +
                             ["Educational research tool - not investment advice. Verify figures against official filings."]})
        meta.to_excel(xw, sheet_name="Notes", index=False)
        xw.sheets["Notes"].column_dimensions["A"].width = 120
    return buf.getvalue()

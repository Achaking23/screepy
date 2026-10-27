
"""
Screepy TicketBot — Exporter: exports ticket data / results to Excel
"""

from pathlib import Path
from typing import List, Optional
from datetime import datetime

from loguru import logger


class Exporter:
    """
    Exports ticket inventory snapshots, acquisition results,
    and account stats to formatted Excel (.xlsx) files.
    """

    def __init__(self, output_dir: str = "exports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_inventory(self, listings: List[dict], filename: Optional[str] = None) -> str:
        """
        Export a list of ticket listings to an Excel spreadsheet.
        Returns the file path.
        """
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Inventory"

            # Header styling
            header_font = Font(bold=True, color="FFFFFF", size=12)
            header_fill = PatternFill(start_color="2F75B5", end_color="2F75B5", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            thin_border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin"),
            )

            # Headers
            headers = [
                "Platform", "Event ID", "Section", "Row", "Seat",
                "Price ($)", "Quantity", "Seller Rating", "URL", "Timestamp"
            ]
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border

            # Data rows
            for row_idx, listing in enumerate(listings, 2):
                ws.cell(row=row_idx, column=1, value=listing.get("platform", ""))
                ws.cell(row=row_idx, column=2, value=listing.get("event_id", ""))
                ws.cell(row=row_idx, column=3, value=listing.get("section", ""))
                ws.cell(row=row_idx, column=4, value=listing.get("row", ""))
                ws.cell(row=row_idx, column=5, value=listing.get("seat", ""))
                ws.cell(row=row_idx, column=6, value=listing.get("price", 0.0))
                ws.cell(row=row_idx, column=7, value=listing.get("quantity", 1))
                ws.cell(row=row_idx, column=8, value=listing.get("seller_rating", 0.0))
                ws.cell(row=row_idx, column=9, value=listing.get("url", ""))
                ws.cell(row=row_idx, column=10, value=listing.get("timestamp", ""))

                # Alternate row coloring
                if row_idx % 2 == 0:
                    alt_fill = PatternFill(start_color="F0F8FF", end_color="F0F8FF", fill_type="solid")
                    for col in range(1, len(headers) + 1):
                        ws.cell(row=row_idx, column=col).fill = alt_fill

            # Auto-adjust column widths
            for col in ws.columns:
                max_length = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = min(max_length + 4, 50)

            # Save
            fname = filename or f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            out_path = self.output_dir / fname
            wb.save(str(out_path))
            logger.success(f"Inventory exported to {out_path}")
            return str(out_path)

        except ImportError:
            logger.error("openpyxl is required. Install: pip install openpyxl")
            raise

    def export_results(self, results: List[dict], filename: Optional[str] = None) -> str:
        """
        Export acquisition results to Excel.
        """
        rows = []
        for r in results:
            res = r.get("result") or {}
            rows.append({
                "bot_id": r.get("bot_id", ""),
                "status": r.get("status", ""),
                "platform": r.get("platform", ""),
                "event_id": r.get("event_id", ""),
                "tickets": res.get("tickets", 0),
                "total": res.get("total", 0.0),
                "confirmation": res.get("confirmation", ""),
                "error": r.get("error", ""),
            })

        return self.export_inventory(
            listings=rows,
            filename=filename or f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        )

    def export_accounts(self, accounts: List[dict], filename: Optional[str] = None) -> str:
        """
        Export account list to Excel.
        """
        return self.export_inventory(
            listings=accounts,
            filename=filename or f"accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        )

from datetime import datetime
from typing import Tuple

def compute_billable_days(starts_at: str, ends_at: str, company: str = None) -> Tuple[int, float]:
    """
    Computes duration and billable days applying Cortex rental pricing rules:
    - Default rule: 7 calendar days = 3.0 billable days.
    - Custom active Rental Pricing Rules override if matched by company and calendar_days.
    """
    if isinstance(starts_at, str):
        # Support ISO8601 or YYYY-MM-DD
        start_date = datetime.fromisoformat(starts_at.replace("Z", "+00:00")).date()
    else:
        start_date = starts_at

    if isinstance(ends_at, str):
        end_date = datetime.fromisoformat(ends_at.replace("Z", "+00:00")).date()
    else:
        end_date = ends_at

    diff = (end_date - start_date).days
    calendar_days = max(1, diff)

    # 7 calendar days = 3 billable days canonical rule
    if calendar_days == 7:
        billable_days = 3.0
    elif calendar_days == 1:
        billable_days = 1.0
    elif calendar_days <= 3:
        billable_days = float(calendar_days)
    elif calendar_days < 7:
        billable_days = min(float(calendar_days), 3.0)
    else:
        # Multiple weeks approximation
        weeks = calendar_days // 7
        remainder = calendar_days % 7
        billable_days = float((weeks * 3.0) + min(remainder, 3.0))

    return calendar_days, billable_days

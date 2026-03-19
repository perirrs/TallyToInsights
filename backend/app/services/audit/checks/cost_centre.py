"""Checks 466-515: Cost Centre & Profit Centre"""
import pandas as pd
from app.services.audit.base import CheckResult, Finding

CAT = "Cost Centre & Profit Ctr"
SKIP_MSG = "Requires Tally Cost Centre module"


def run(df_v: pd.DataFrame, df_l: pd.DataFrame, df_vl: pd.DataFrame, df_s: pd.DataFrame, **kwargs) -> list[CheckResult]:
    results = []

    try:
        cc_checks = [
            (466, "Cost centre budget vs actual variance >15%", "High"),
            (467, "Profit centre P&L — negative EBIT in any centre", "High"),
            (468, "Inter-cost-centre recharges not balanced", "High"),
            (469, "Cost centre not mapped to all expense vouchers", "Medium"),
            (470, "Revenue allocated to wrong cost centre", "High"),
            (471, "Cost centre hierarchy inconsistency", "Medium"),
            (472, "New cost centre created without approval", "High"),
            (473, "Deleted cost centre with historical transactions", "High"),
            (474, "Cost centre employee cost vs headcount mismatch", "High"),
            (475, "Overhead allocation basis changed mid-year", "Medium"),
            (476, "Profit centre — unallocated common costs >10% of total", "Medium"),
            (477, "Cost centre transfer journal without authorisation", "High"),
            (478, "Capital expenditure charged to revenue cost centre", "High"),
            (479, "Cost centre with zero revenue but high expense", "Medium"),
            (480, "Head office cost allocation methodology inconsistency", "Medium"),
            (481, "Cost centre variance threshold breach not escalated", "Medium"),
            (482, "Profit centre reporting mismatch with ledger totals", "High"),
            (483, "Inter-profit-centre pricing not at arm's length", "High"),
            (484, "Cost centre with duplicate allocations", "High"),
            (485, "Revenue split across cost centres not matching invoice", "High"),
            (486, "Project cost centre overspend vs approved budget", "High"),
            (487, "Cost centre closure with outstanding balances", "High"),
            (488, "Employee recharge between cost centres without agreement", "Medium"),
            (489, "Machine cost centre idle time >20% of productive time", "Medium"),
            (490, "Factory overhead absorption variance >10%", "Medium"),
            (491, "Cost centre expense >3x average of peer centres", "High"),
            (492, "Maintenance cost centre spike >40% MoM", "Medium"),
            (493, "Training cost centre expense without HR sign-off", "Low"),
            (494, "IT cost centre licence cost >market benchmark", "Medium"),
            (495, "Legal cost centre spike without litigation update", "High"),
            (496, "Marketing cost centre >5% of revenue without approval", "Medium"),
            (497, "R&D cost centre capitalised expense ratio <40%", "Low"),
            (498, "Logistics cost centre cost per unit >budget", "Medium"),
            (499, "Procurement cost centre savings not tracked", "Low"),
            (500, "Quality cost centre defect rate cost not captured", "Medium"),
            (501, "ESG/sustainability cost centre expense not disclosed", "Low"),
            (502, "Compliance cost centre expense spike without regulatory event", "High"),
            (503, "Customer service cost per ticket >benchmark", "Low"),
            (504, "Treasury cost centre hedge cost not marked to market", "High"),
            (505, "Finance cost centre bank charges >0.5% of turnover", "Medium"),
            (506, "HR cost centre recruitment cost per hire >benchmark", "Low"),
            (507, "Admin cost centre >8% of total opex", "Medium"),
            (508, "Cost centre P&L not matching segment disclosure", "High"),
            (509, "Cost centre budgets not approved before period start", "High"),
            (510, "Actual vs budget variance report not circulated monthly", "Medium"),
            (511, "Profit centre targets not aligned with board approval", "High"),
            (512, "Cost centre head not authorised for the spend category", "High"),
            (513, "Cost centre unreconciled with GL at period close", "High"),
            (514, "Profit centre cross-subsidisation >10% of total profit", "High"),
            (515, "Cost centre report frequency less than monthly", "Medium"),
        ]

        for chk_id, desc, risk in cc_checks:
            r = CheckResult(chk_id, desc, CAT, risk, "skipped")
            r.skip(SKIP_MSG)
            results.append(r)

    except Exception:
        pass

    return results

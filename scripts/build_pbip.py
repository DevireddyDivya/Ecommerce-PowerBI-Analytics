"""Writes the Power BI Project (PBIP): semantic model in TMDL plus a 5-page report.

Run:  python scripts/build_pbip.py      then open EcommerceAnalytics.pbip in Power BI Desktop and Refresh.
The CSVs are read from the DataFolder parameter (default: this repo's data folder).
"""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "EcommerceAnalytics"
MODEL = ROOT / f"{NAME}.SemanticModel"
REPORT = ROOT / f"{NAME}.Report"
DATA_FOLDER = str(ROOT / "data") + "\\"

T = "\t"


def gid():
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{NAME}-{gid.n}")) if (setattr(gid, "n", gid.n + 1) or True) else ""


gid.n = 0


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


# ------------------------------------------------------------------------------------------------ semantic model
M_TYPE = {"string": "type text", "dateTime": "type date", "int64": "Int64.Type", "double": "type number"}

# table -> (csv file, [(column, dataType, extra properties)])
SOURCE_TABLES = {
    "customers": ("customers", [
        ("customer_id", "string", {}), ("gender", "string", {}), ("age_group", "string", {}), ("city", "string", {}),
        ("state", "string", {"dataCategory": "StateOrProvince"}), ("region", "string", {}),
        ("signup_date", "dateTime", {"formatString": "dd mmm yyyy"}), ("acquisition_channel", "string", {})]),
    "products": ("products", [
        ("product_id", "string", {}), ("product_name", "string", {}), ("category", "string", {}),
        ("subcategory", "string", {}), ("brand", "string", {}),
        ("unit_price", "double", {"formatString": "₹#,0"}), ("unit_cost", "double", {"formatString": "₹#,0"})]),
    "sessions": ("sessions", [
        ("session_id", "string", {}), ("session_date", "dateTime", {"formatString": "dd mmm yyyy"}),
        ("customer_id", "string", {}), ("channel", "string", {}), ("device", "string", {}),
        ("product_view", "int64", {}), ("add_to_cart", "int64", {}), ("checkout", "int64", {}),
        ("purchase", "int64", {}), ("order_id", "string", {})]),
    "orders": ("orders", [
        ("order_id", "string", {}), ("customer_id", "string", {}),
        ("order_date", "dateTime", {"formatString": "dd mmm yyyy"}), ("order_status", "string", {}),
        ("payment_method", "string", {}), ("channel", "string", {}), ("device", "string", {}),
        ("promised_days", "int64", {}), ("delivery_days", "int64", {}), ("shipping_fee", "double", {"formatString": "₹#,0"})]),
    "order_items": ("order_items", [
        ("order_id", "string", {}), ("line_number", "int64", {}), ("product_id", "string", {}),
        ("quantity", "int64", {}), ("unit_price", "double", {"formatString": "₹#,0"}), ("discount_pct", "int64", {}),
        ("line_revenue", "double", {"formatString": "₹#,0"}), ("line_cost", "double", {"formatString": "₹#,0"})]),
    "reviews": ("reviews", [
        ("order_id", "string", {}), ("review_score", "int64", {}), ("review_date", "dateTime", {"formatString": "dd mmm yyyy"})]),
}
HIDDEN = {("sessions", "order_id"), ("order_items", "line_number")}

# RFM-style customer columns. Row context + FILTER (no CALCULATE), so the columns do not depend on each other
# through context transition (which would be a circular dependency).
CUSTOMER_CALC_COLUMNS = [
    ("Order Count", "int64", "", 'COUNTROWS(FILTER(orders, orders[customer_id] = customers[customer_id] && orders[order_status] <> "Cancelled"))'),
    ("Lifetime Revenue", "double", "₹#,0",
     'SUMX(FILTER(order_items, RELATED(orders[customer_id]) = customers[customer_id] && RELATED(orders[order_status]) IN {"Delivered", "Shipped"}), order_items[line_revenue])'),
    ("Last Order Date", "dateTime", "dd mmm yyyy",
     'MAXX(FILTER(orders, orders[customer_id] = customers[customer_id] && orders[order_status] <> "Cancelled"), orders[order_date])'),
    ("Days Since Last Order", "int64", "",
     'IF(NOT ISBLANK(customers[Last Order Date]), DATEDIFF(customers[Last Order Date], MAX(orders[order_date]), DAY))'),
    ("Customer Type", "string", "",
     'SWITCH(TRUE(), customers[Order Count] = 0, "No Purchase", customers[Order Count] = 1, "One-time", "Repeat")'),
    ("Segment", "string", "",
     'SWITCH(TRUE(), customers[Order Count] = 0, "Never Purchased", '
     'customers[Order Count] >= 3 && customers[Days Since Last Order] <= 90, "Champions", '
     'customers[Order Count] >= 3, "Loyal", '
     'customers[Order Count] = 2 && customers[Days Since Last Order] <= 120, "Promising", '
     'customers[Days Since Last Order] <= 60, "New", '
     'customers[Days Since Last Order] > 270, "Lost", "At Risk")'),
]

COMPLETED = 'orders[order_status] IN {"Delivered", "Shipped"}'
MEASURES = [  # (folder, name, DAX, format)
    ("Sales", "Gross Revenue", "SUM(order_items[line_revenue])", "₹#,0"),
    ("Sales", "Net Revenue", f"CALCULATE([Gross Revenue], {COMPLETED})", "₹#,0"),
    ("Sales", "Cost", f"CALCULATE(SUM(order_items[line_cost]), {COMPLETED})", "₹#,0"),
    ("Sales", "Gross Profit", "[Net Revenue] - [Cost]", "₹#,0"),
    ("Sales", "Profit Margin %", "DIVIDE([Gross Profit], [Net Revenue])", "0.0%"),
    ("Sales", "Orders", "DISTINCTCOUNT(order_items[order_id])", "#,0"),
    ("Sales", "Completed Orders", f"CALCULATE([Orders], {COMPLETED})", "#,0"),
    ("Sales", "Average Order Value", "DIVIDE([Net Revenue], [Completed Orders])", "₹#,0"),
    ("Sales", "Units Sold", f"CALCULATE(SUM(order_items[quantity]), {COMPLETED})", "#,0"),
    ("Sales", "Avg Discount %", "DIVIDE(AVERAGE(order_items[discount_pct]), 100)", "0.0%"),
    ("Time Intelligence", "Net Revenue PY", "CALCULATE([Net Revenue], SAMEPERIODLASTYEAR('Date'[Date]))", "₹#,0"),
    ("Time Intelligence", "Revenue YoY %", "DIVIDE([Net Revenue] - [Net Revenue PY], [Net Revenue PY])", "+0.0%;-0.0%;0.0%"),
    ("Time Intelligence", "Net Revenue YTD", "TOTALYTD([Net Revenue], 'Date'[Date])", "₹#,0"),
    ("Time Intelligence", "Orders PY", "CALCULATE([Completed Orders], SAMEPERIODLASTYEAR('Date'[Date]))", "#,0"),
    ("Time Intelligence", "Orders YoY %", "DIVIDE([Completed Orders] - [Orders PY], [Orders PY])", "+0.0%;-0.0%;0.0%"),
    ("Customers", "Customers", "CALCULATE(DISTINCTCOUNT(orders[customer_id]), CROSSFILTER(order_items[order_id], orders[order_id], Both))", "#,0"),
    ("Customers", "Repeat Customers",
     "COUNTROWS(FILTER(VALUES(orders[customer_id]), CALCULATE(DISTINCTCOUNT(orders[order_id]), orders[order_status] <> \"Cancelled\") > 1))", "#,0"),
    ("Customers", "Repeat Customer Rate", "DIVIDE([Repeat Customers], DISTINCTCOUNT(orders[customer_id]))", "0.0%"),
    ("Customers", "New Customers",
     "VAR PeriodStart = MIN('Date'[Date]) RETURN COUNTROWS(FILTER(VALUES(orders[customer_id]), CALCULATE(MIN(orders[order_date]), ALL('Date')) >= PeriodStart))", "#,0"),
    ("Customers", "Revenue per Customer", "DIVIDE([Net Revenue], [Customers])", "₹#,0"),
    ("Funnel", "Sessions", "COUNTROWS(sessions)", "#,0"),
    ("Funnel", "Product Views", "SUM(sessions[product_view])", "#,0"),
    ("Funnel", "Add to Cart", "SUM(sessions[add_to_cart])", "#,0"),
    ("Funnel", "Checkouts", "SUM(sessions[checkout])", "#,0"),
    ("Funnel", "Purchases", "SUM(sessions[purchase])", "#,0"),
    ("Funnel", "Conversion Rate", "DIVIDE([Purchases], [Sessions])", "0.00%"),
    ("Funnel", "Add to Cart Rate", "DIVIDE([Add to Cart], [Sessions])", "0.0%"),
    ("Funnel", "Cart Abandonment %", "1 - DIVIDE([Purchases], [Add to Cart])", "0.0%"),
    ("Funnel", "Funnel Count",
     "SWITCH(SELECTEDVALUE('Funnel Stage'[Stage]), \"Sessions\", [Sessions], \"Product View\", [Product Views], "
     "\"Add to Cart\", [Add to Cart], \"Checkout\", [Checkouts], \"Purchase\", [Purchases])", "#,0"),
    ("Funnel", "Funnel % of Sessions", "DIVIDE([Funnel Count], [Sessions])", "0.0%"),
    ("Operations", "Cancellation Rate", "DIVIDE(CALCULATE([Orders], orders[order_status] = \"Cancelled\"), [Orders])", "0.0%"),
    ("Operations", "Return Rate", "DIVIDE(CALCULATE([Orders], orders[order_status] = \"Returned\"), [Orders])", "0.0%"),
    ("Operations", "Avg Delivery Days", "AVERAGE(orders[delivery_days])", "0.0"),
    ("Operations", "On-Time Delivery %",
     "DIVIDE(COUNTROWS(FILTER(orders, NOT ISBLANK(orders[delivery_days]) && orders[delivery_days] <= orders[promised_days])), "
     "COUNTROWS(FILTER(orders, NOT ISBLANK(orders[delivery_days]))))", "0.0%"),
    ("Operations", "Avg Review Score", "AVERAGE(reviews[review_score])", "0.00"),
    ("Operations", "Positive Review %", "DIVIDE(COUNTROWS(FILTER(reviews, reviews[review_score] >= 4)), COUNTROWS(reviews))", "0.0%"),
]


def column_tmdl(name, dtype, props=None, source=None, hidden=False, expression=None):
    props = props or {}
    head = f"{T}column '{name}'" if " " in name else f"{T}column {name}"
    if expression:
        head += f" = {expression}"
    lines = [head, f"{T*2}dataType: {dtype}"]
    if "formatString" in props:
        lines.append(f"{T*2}formatString: {props['formatString']}")
    if hidden:
        lines.append(f"{T*2}isHidden")
    if props.get("isKey"):
        lines.append(f"{T*2}isKey")
    if "dataCategory" in props:
        lines.append(f"{T*2}dataCategory: {props['dataCategory']}")
    lines.append(f"{T*2}lineageTag: {gid()}")
    summarize = "sum" if dtype in ("int64", "double") and not props.get("noSum") and not name.endswith("_days") else "none"
    if name in ("promised_days", "delivery_days", "review_score", "discount_pct", "Days Since Last Order", "Year",
                "Month Number", "Weekday Number", "Step", "line_number", "Order Count"):
        summarize = "none"
    lines.append(f"{T*2}summarizeBy: {summarize}")
    if source:
        lines.append(f"{T*2}sourceColumn: {source}")
    if props.get("isNameInferred"):
        lines.append(f"{T*2}isNameInferred")
    if "sortByColumn" in props:
        lines.append(f"{T*2}sortByColumn: '{props['sortByColumn']}'" if " " in props["sortByColumn"] else f"{T*2}sortByColumn: {props['sortByColumn']}")
    lines.append("")
    lines.append(f"{T*2}annotation SummarizationSetBy = Automatic")
    return "\n".join(lines) + "\n"


def m_partition(table, csv_name, columns):
    types = ", ".join(f'{{"{c}", {M_TYPE[t]}}}' for c, t, _ in columns)
    src = [
        "let",
        f'    Source = Csv.Document(File.Contents(DataFolder & "{csv_name}.csv"), [Delimiter = ",", Columns = {len(columns)}, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
        f"    Typed = Table.TransformColumnTypes(Promoted, {{{types}}})",
        "in",
        "    Typed",
    ]
    body = "\n".join(f"{T*4}{line}" for line in src)
    return f"{T}partition {table} = m\n{T*2}mode: import\n{T*2}source =\n{body}\n"


tables = {}
for table, (csv_name, cols) in SOURCE_TABLES.items():
    out = [f"table {table}", f"{T}lineageTag: {gid()}", ""]
    for col, dtype, props in cols:
        out.append(column_tmdl(col, dtype, props, source=col, hidden=(table, col) in HIDDEN))
    if table == "customers":
        for col, dtype, fmt, dax in CUSTOMER_CALC_COLUMNS:
            out.append(column_tmdl(col, dtype, {"formatString": fmt} if fmt else {}, expression=dax))
    out.append(m_partition(table, csv_name, cols))
    out.append(f"{T}annotation PBI_ResultType = Table\n")
    tables[table] = "\n".join(out)

# Date table (calculated, marked as date table)
date_dax = ("ADDCOLUMNS(CALENDAR(DATE(2024, 1, 1), DATE(2025, 12, 31)), \"Year\", YEAR([Date]), \"Month Number\", MONTH([Date]), "
            "\"Month\", FORMAT([Date], \"mmm\"), \"Year Month\", FORMAT([Date], \"yyyy-mm\"), \"Quarter\", \"Q\" & QUARTER([Date]), "
            "\"Weekday\", FORMAT([Date], \"ddd\"), \"Weekday Number\", WEEKDAY([Date], 2), "
            "\"Day Type\", IF(WEEKDAY([Date], 2) > 5, \"Weekend\", \"Weekday\"))")
date_cols = [("Date", "dateTime", {"isKey": True, "formatString": "dd mmm yyyy"}), ("Year", "int64", {}),
             ("Month Number", "int64", {}), ("Month", "string", {"sortByColumn": "Month Number"}),
             ("Year Month", "string", {}), ("Quarter", "string", {}), ("Weekday", "string", {"sortByColumn": "Weekday Number"}),
             ("Weekday Number", "int64", {}), ("Day Type", "string", {})]
out = ["table Date", f"{T}dataCategory: Time", f"{T}lineageTag: {gid()}", ""]
for col, dtype, props in date_cols:
    out.append(column_tmdl(col, dtype, {**props, "isNameInferred": True}, source=f"[{col}]"))
out.append(f"{T}partition Date = calculated\n{T*2}mode: import\n{T*2}source = {date_dax}\n")
out.append(f"{T}annotation PBI_Id = {uuid.uuid5(uuid.NAMESPACE_URL, 'date')}\n")
tables["Date"] = "\n".join(out)

# Funnel stages (disconnected table that drives the funnel visual through [Funnel Count])
funnel_dax = ('DATATABLE("Stage", STRING, "Step", INTEGER, {{"Sessions", 1}, {"Product View", 2}, '
              '{"Add to Cart", 3}, {"Checkout", 4}, {"Purchase", 5}})')
out = ["table 'Funnel Stage'", f"{T}lineageTag: {gid()}", ""]
out.append(column_tmdl("Stage", "string", {"sortByColumn": "Step", "isNameInferred": True}, source="[Stage]"))
out.append(column_tmdl("Step", "int64", {"isNameInferred": True}, source="[Step]"))
out.append(f"{T}partition 'Funnel Stage' = calculated\n{T*2}mode: import\n{T*2}source = {funnel_dax}\n")
tables["Funnel Stage"] = "\n".join(out)

# Measures table: one hidden placeholder column, all measures grouped in display folders
out = ["table Measures", f"{T}lineageTag: {gid()}", ""]
for folder, name, dax, fmt in MEASURES:
    mname = f"'{name}'" if any(ch in name for ch in " %-") else name
    out.append(f"{T}measure {mname} = {dax}\n{T*2}formatString: {fmt}\n{T*2}displayFolder: {folder}\n{T*2}lineageTag: {gid()}\n")
out.append(column_tmdl("Placeholder", "int64", {"isNameInferred": True}, source="[Placeholder]", hidden=True))
out.append(f"{T}partition Measures = calculated\n{T*2}mode: import\n{T*2}source = ROW(\"Placeholder\", 0)\n")
tables["Measures"] = "\n".join(out)

RELATIONSHIPS = [
    ("orders.customer_id", "customers.customer_id"),
    ("order_items.order_id", "orders.order_id"),
    ("order_items.product_id", "products.product_id"),
    ("reviews.order_id", "orders.order_id"),
    ("orders.order_date", "Date.Date"),
    ("sessions.session_date", "Date.Date"),
    ("sessions.customer_id", "customers.customer_id"),
]


def ref(col):
    table, c = col.split(".")
    table = f"'{table}'" if " " in table else table
    return f"{table}.{c}"


rel_tmdl = "\n".join(
    f"relationship {gid()}\n{T}fromColumn: {ref(a)}\n{T}toColumn: {ref(b)}\n" for a, b in RELATIONSHIPS)

order = ["customers", "products", "sessions", "orders", "order_items", "reviews", "Date", "Funnel Stage", "Measures"]
model_tmdl = "\n".join([
    "model Model",
    f"{T}culture: en-US",
    f"{T}defaultPowerBIDataSourceVersion: powerBI_V3",
    f"{T}sourceQueryCulture: en-IN",
    f"{T}dataAccessOptions",
    f"{T*2}legacyRedirects",
    f"{T*2}returnErrorValuesAsNull",
    "",
    "annotation PBI_QueryOrder = " + json.dumps(["DataFolder"] + [t for t in order if t in SOURCE_TABLES]),
    "",
    "annotation __PBI_TimeIntelligenceEnabled = 0",
    "",
] + [f"ref table {('%s' % t) if ' ' not in t else repr(t).replace(chr(34), chr(39))}" for t in order]) + "\n"

expressions_tmdl = (
    f'expression DataFolder = "{DATA_FOLDER}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
    f"{T}lineageTag: {gid()}\n\n{T}annotation PBI_ResultType = Text\n")

defn = MODEL / "definition"
write(defn / "database.tmdl", "database\n\tcompatibilityLevel: 1567\n")
write(defn / "model.tmdl", model_tmdl)
write(defn / "expressions.tmdl", expressions_tmdl)
write(defn / "relationships.tmdl", rel_tmdl)
for t, text in tables.items():
    write(defn / "tables" / f"{t}.tmdl", text)
write(MODEL / "definition.pbism", json.dumps({"version": "4.0", "settings": {}}, indent=2))

# ------------------------------------------------------------------------------------------------ report
ENTITY_ALIAS = {}


def field(entity, prop, measure=False):
    return (entity, prop, measure)


def visual(vtype, x, y, w, h, title, roles, extra_objects=None):
    """roles: {projectionRole: [field(...), ...]}"""
    aliases, frm, select, projections = {}, [], [], {}
    for role, fields in roles.items():
        projections[role] = []
        for entity, prop, is_measure in fields:
            if entity not in aliases:
                aliases[entity] = f"t{len(aliases)}"
                frm.append({"Name": aliases[entity], "Entity": entity, "Type": 0})
            name = f"{entity}.{prop}"
            kind = "Measure" if is_measure else "Column"
            item = {kind: {"Expression": {"SourceRef": {"Source": aliases[entity]}}, "Property": prop}, "Name": name}
            if not any(s["Name"] == name for s in select):
                select.append(item)
            projections[role].append({"queryRef": name})
    vid = uuid.uuid5(uuid.NAMESPACE_URL, f"{title}-{x}-{y}").hex[:20]
    vc = {"title": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}},
                                    "text": {"expr": {"Literal": {"Value": "'" + title.replace("'", "''") + "'"}}}}}]}
    single = {"visualType": vtype, "projections": projections,
              "prototypeQuery": {"Version": 2, "From": frm, "Select": select},
              "drillFilterOtherVisuals": True, "vcObjects": vc}
    if extra_objects:
        single["objects"] = extra_objects
    config = {"name": vid, "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}}],
              "singleVisual": single}
    return {"x": x, "y": y, "z": 0, "width": w, "height": h, "config": json.dumps(config), "filters": "[]"}


M = lambda name: field("Measures", name, True)
C = lambda table, col: field(table, col)
SLICER_OBJ = {"data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Dropdown'"}}}}}]}


def slicers(y=8):
    return [visual("slicer", 8, y, 200, 60, "Year", {"Values": [C("Date", "Year")]}, SLICER_OBJ),
            visual("slicer", 216, y, 200, 60, "Region", {"Values": [C("customers", "region")]}, SLICER_OBJ),
            visual("slicer", 424, y, 200, 60, "Category", {"Values": [C("products", "category")]}, SLICER_OBJ)]


def cards(measures, y=76):
    w = (1264 - 8 * (len(measures) - 1)) // len(measures)
    return [visual("card", 8 + i * (w + 8), y, w, 110, m, {"Values": [M(m)]}) for i, m in enumerate(measures)]


PAGES = [
    ("Executive Overview", slicers() + cards(["Net Revenue", "Gross Profit", "Profit Margin %", "Completed Orders",
                                              "Average Order Value", "Conversion Rate"]) + [
        visual("lineChart", 8, 194, 820, 260, "Net Revenue vs Last Year by Month",
               {"Category": [C("Date", "Year Month")], "Y": [M("Net Revenue"), M("Net Revenue PY")]}),
        visual("donutChart", 836, 194, 436, 260, "Net Revenue by Category",
               {"Category": [C("products", "category")], "Y": [M("Net Revenue")]}),
        visual("clusteredBarChart", 8, 462, 620, 250, "Net Revenue by Region",
               {"Category": [C("customers", "region")], "Y": [M("Net Revenue")]}),
        visual("clusteredColumnChart", 636, 462, 636, 250, "Orders by Payment Method",
               {"Category": [C("orders", "payment_method")], "Y": [M("Completed Orders")]}),
    ]),
    ("Sales & Products", slicers() + cards(["Net Revenue", "Revenue YoY %", "Units Sold", "Avg Discount %", "Net Revenue YTD"]) + [
        visual("clusteredBarChart", 8, 194, 620, 518, "Top Subcategories by Net Revenue",
               {"Category": [C("products", "subcategory")], "Y": [M("Net Revenue")]}),
        visual("clusteredColumnChart", 636, 194, 636, 250, "Profit Margin % by Category",
               {"Category": [C("products", "category")], "Y": [M("Profit Margin %")]}),
        visual("tableEx", 636, 452, 636, 260, "Brand Performance",
               {"Values": [C("products", "brand"), M("Net Revenue"), M("Units Sold"), M("Profit Margin %"), M("Return Rate")]}),
    ]),
    ("Customers", slicers() + cards(["Customers", "New Customers", "Repeat Customers", "Repeat Customer Rate",
                                      "Revenue per Customer"]) + [
        visual("clusteredBarChart", 8, 194, 620, 250, "Customers by Segment (RFM)",
               {"Category": [C("customers", "Segment")], "Y": [M("Customers")]}),
        visual("donutChart", 636, 194, 636, 250, "Net Revenue by Customer Type",
               {"Category": [C("customers", "Customer Type")], "Y": [M("Net Revenue")]}),
        visual("clusteredColumnChart", 8, 452, 620, 260, "Net Revenue by Age Group",
               {"Category": [C("customers", "age_group")], "Y": [M("Net Revenue")]}),
        visual("tableEx", 636, 452, 636, 260, "Top Cities",
               {"Values": [C("customers", "city"), M("Customers"), M("Net Revenue"), M("Average Order Value")]}),
    ]),
    ("Funnel & Conversion", [visual("slicer", 8, 8, 200, 60, "Year", {"Values": [C("Date", "Year")]}, SLICER_OBJ),
                             visual("slicer", 216, 8, 200, 60, "Channel", {"Values": [C("sessions", "channel")]}, SLICER_OBJ),
                             visual("slicer", 424, 8, 200, 60, "Device", {"Values": [C("sessions", "device")]}, SLICER_OBJ)]
     + cards(["Sessions", "Add to Cart Rate", "Conversion Rate", "Cart Abandonment %"]) + [
        visual("funnel", 8, 194, 620, 518, "Purchase Funnel",
               {"Category": [C("Funnel Stage", "Stage")], "Y": [M("Funnel Count")]}),
        visual("clusteredBarChart", 636, 194, 636, 250, "Conversion Rate by Channel",
               {"Category": [C("sessions", "channel")], "Y": [M("Conversion Rate")]}),
        visual("clusteredColumnChart", 636, 452, 636, 260, "Conversion Rate by Device",
               {"Category": [C("sessions", "device")], "Y": [M("Conversion Rate")]}),
    ]),
    ("Operations & Reviews", slicers() + cards(["Avg Delivery Days", "On-Time Delivery %", "Cancellation Rate",
                                                 "Return Rate", "Avg Review Score"]) + [
        visual("clusteredBarChart", 8, 194, 620, 250, "Avg Delivery Days by Region",
               {"Category": [C("customers", "region")], "Y": [M("Avg Delivery Days")]}),
        visual("clusteredColumnChart", 636, 194, 636, 250, "Cancellation Rate by Payment Method",
               {"Category": [C("orders", "payment_method")], "Y": [M("Cancellation Rate")]}),
        visual("lineChart", 8, 452, 820, 260, "Avg Review Score by Month",
               {"Category": [C("Date", "Year Month")], "Y": [M("Avg Review Score")]}),
        visual("clusteredColumnChart", 836, 452, 436, 260, "Return Rate by Category",
               {"Category": [C("products", "category")], "Y": [M("Return Rate")]}),
    ]),
]

sections = []
for i, (title, visuals) in enumerate(PAGES):
    sections.append({"name": f"ReportSection{i + 1}", "displayName": title, "displayOption": 1, "width": 1280,
                     "height": 720, "ordinal": i, "filters": "[]", "config": "{}", "visualContainers": visuals})

report_json = {
    "config": json.dumps({"version": "5.43", "themeCollection": {}, "activeSectionIndex": 0,
                          "defaultDrillFilterOtherVisuals": True, "settings": {"useStylableVisualContainerHeader": True}}),
    "layoutOptimization": 0,
    "resourcePackages": [],
    "sections": sections,
    "filters": "[]",
}
write(REPORT / "report.json", json.dumps(report_json, indent=2, ensure_ascii=False))
write(REPORT / "definition.pbir", json.dumps(
    {"version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}}, indent=2))
write(ROOT / f"{NAME}.pbip", json.dumps(
    {"version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}], "settings": {"enableAutoRecovery": True}}, indent=2))

print(f"Wrote {NAME}.pbip: {len(tables)} tables, {len(MEASURES)} measures, {len(RELATIONSHIPS)} relationships, "
      f"{len(PAGES)} pages, {sum(len(v) for _, v in PAGES)} visuals")

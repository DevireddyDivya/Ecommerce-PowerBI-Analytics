# E-commerce Funnel & Customer Analytics (Power BI)

An end-to-end Power BI project for an Indian online store (2024-2025): where visitors drop out of the purchase
funnel, which products and regions drive profit, who the repeat customers are, and how delivery affects reviews.

Built as a **Power BI Project (`.pbip`)**: the semantic model is stored as TMDL text and the report as JSON, so
every table, relationship and DAX measure is readable and version-controlled in Git.

## Business questions

1. How are revenue, profit and orders trending, and how do they compare with last year?
2. Where in the funnel (visit → product view → add to cart → checkout → purchase) do shoppers drop off, and how
   does conversion differ by channel and device?
3. Which categories, subcategories and brands bring revenue versus margin?
4. How many customers come back, which RFM segment are they in, and which cities and age groups spend most?
5. How do delivery time, cancellations and returns vary by region and payment method, and how do they affect reviews?

## Report pages

| Page | What it shows |
|---|---|
| **Executive Overview** | Net revenue, gross profit, margin, orders, AOV, conversion; revenue vs last year by month; revenue by category, region and payment method |
| **Sales & Products** | YoY growth, units, discount, YTD revenue; top subcategories; margin by category; brand table with return rate |
| **Customers** | Customers, new, repeat, repeat rate, revenue per customer; RFM segments; one-time vs repeat revenue; age groups; top cities |
| **Funnel & Conversion** | Sessions, add-to-cart rate, conversion, cart abandonment; purchase funnel; conversion by channel and device |
| **Operations & Reviews** | Delivery days, on-time %, cancellation and return rates, review score; by region, payment method, month and category |

Every page has Year, Region and Category slicers (the funnel page uses Year, Channel and Device).

## Data model

Star schema, imported from CSV with Power Query (one `DataFolder` parameter for the file location):

```
                 customers (1) ──┬──< orders (*) >── (1) Date (1) ──< sessions (*)
                                 │        │                               │
                                 │        └──< order_items (*) >── (1) products
                                 │        └──< reviews (*)
                                 └───────────────────────────────────────< sessions
```

| Table | Rows | Grain |
|---|---|---|
| `sessions` | 97,460 | one website visit, with funnel flags (product view, add to cart, checkout, purchase) |
| `orders` | 5,488 | one order: status, payment, channel, device, promised and actual delivery days |
| `order_items` | 8,686 | one order line: product, quantity, discount, revenue, cost |
| `reviews` | 2,813 | one review per reviewed order |
| `customers` | 9,000 | demographics, city / region, signup channel, plus RFM calculated columns |
| `products` | 124 | category, subcategory, brand, price, cost |
| `Date` | 731 | calculated date table (marked as date table) |
| `Funnel Stage` | 5 | disconnected table that drives the funnel visual |

## DAX highlights

All 36 measures live in a dedicated **Measures** table, grouped into display folders (Sales, Time Intelligence,
Customers, Funnel, Operations). A few worth explaining in an interview:

```DAX
Net Revenue = CALCULATE([Gross Revenue], orders[order_status] IN {"Delivered", "Shipped"})

Revenue YoY % = DIVIDE([Net Revenue] - [Net Revenue PY], [Net Revenue PY])
Net Revenue PY = CALCULATE([Net Revenue], SAMEPERIODLASTYEAR('Date'[Date]))

-- customers with more than one (non-cancelled) order in the selected period
Repeat Customers =
COUNTROWS(FILTER(VALUES(orders[customer_id]),
    CALCULATE(DISTINCTCOUNT(orders[order_id]), orders[order_status] <> "Cancelled") > 1))

-- one measure feeds all five funnel stages from the disconnected 'Funnel Stage' table
Funnel Count =
SWITCH(SELECTEDVALUE('Funnel Stage'[Stage]),
    "Sessions", [Sessions], "Product View", [Product Views], "Add to Cart", [Add to Cart],
    "Checkout", [Checkouts], "Purchase", [Purchases])

Cart Abandonment % = 1 - DIVIDE([Purchases], [Add to Cart])
```

**RFM segmentation** is done with calculated columns on `customers` (Order Count, Lifetime Revenue, Last Order
Date, Days Since Last Order, Segment). They use `FILTER` over the related rows instead of `CALCULATE`, because
several `CALCULATE` columns on the same table would depend on each other through context transition and cause a
circular dependency.

## Key insights (from the data)

- Overall conversion is **5.6%**; the biggest drop is between product view and add to cart (64% → 21% of sessions).
- **Email** converts at **10.3%** and **Direct** at 7.2%, against **2.8%** for **Social Media**. **Desktop** converts
  at 8.7% versus 4.3% on **Mobile**, even though mobile brings 64% of sessions.
- **October-November** (Navratri / Diwali sales) is the peak: October orders are about 5× June's.
- **Electronics** brings the most revenue (₹93 lakh) but discounts leave it about **1% margin**; **Beauty** (46%) and
  **Fashion** (38%) are the most profitable categories.
- **Cash on Delivery** orders are cancelled **3×** as often as prepaid orders (11.5% vs 3.7%).
- The **North-East** waits longest for delivery (6.5 days vs about 3.4 in the South and West), and late deliveries
  average **3.5** stars against **4.2** for on-time ones.
- **31%** of buying customers order again, and these repeat customers bring **52%** of revenue.

The data is synthetic (generated by `scripts/generate_data.py` with these patterns built in), so the insights are
illustrations of the analysis, not facts about a real company.

## How to open it

1. Install **Power BI Desktop** (free, Windows).
2. Open `EcommerceAnalytics.pbip`.
3. If the CSVs are not in `D:\ecommerce-powerbi\data\`, go to **Transform data → Manage parameters** and set
   `DataFolder` to the full path of this repo's `data\` folder (ending with `\`), then **Close & Apply**.
4. Click **Refresh**.

To regenerate: `python scripts/generate_data.py` (data) and `python scripts/build_pbip.py` (model and report).

## Tools

Power BI Desktop, Power Query (M), DAX, TMDL / PBIP, Python (data generation), Git and GitHub

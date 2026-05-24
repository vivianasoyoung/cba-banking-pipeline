{{ config(materialized='table') }}

-- Segments customers by average monthly spend over the last 12 calendar months.
-- Dormant months count as ZERO (the original used avg() over active months only,
-- which mis-classified single-spike accounts as Premium).

with monthly as (
    select * from {{ ref('int_customer_monthly_spend') }}
),

bounds as (
    select
        date_trunc('month', max(transaction_month))::date                            as latest_month,
        (date_trunc('month', max(transaction_month)) - interval '11 months')::date   as earliest_month
    from monthly
),

per_account as (
    select
        m.account_id,
        m.customer_id,
        m.account_type,
        sum(m.total_spend)::numeric(18, 2)                            as lifetime_spend,
        sum(case when m.transaction_month >= b.earliest_month
                 then m.total_spend else 0 end)::numeric(18, 2)       as spend_12m,
        count(distinct case when m.transaction_month >= b.earliest_month
                            then m.transaction_month end)             as active_months_12m,
        max(m.total_spend)::numeric(18, 2)                            as best_month_spend,
        max(m.categories_used)                                        as max_categories_in_month
    from monthly m
    cross join bounds b
    group by 1, 2, 3
),

with_avg as (
    select
        *,
        -- Denominator is fixed 12; dormant months count as zero.
        (spend_12m / 12.0)::numeric(18, 2) as avg_monthly_spend
    from per_account
),

segmented as (
    select
        *,
        case
            when avg_monthly_spend >= 5000 then 'Premium'
            when avg_monthly_spend >= 2000 then 'High Value'
            when avg_monthly_spend >= 500  then 'Regular'
            else 'Low Activity'
        end as customer_segment
    from with_avg
)

select * from segmented

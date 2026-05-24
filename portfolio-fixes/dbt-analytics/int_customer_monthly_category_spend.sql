-- Renamed from int_customer_monthly_spend. The grain includes merchant_category.
with transactions as (
    select *
    from {{ ref('stg_transactions') }}
    where transaction_type = 'DEBIT'
),

accounts as (
    select * from {{ ref('stg_accounts') }}
),

aggregated as (
    select
        t.account_id,
        a.customer_id,
        a.account_type,
        t.transaction_month,
        t.merchant_category,
        count(*)                       as transaction_count,
        sum(t.amount)::numeric(18, 2)  as total_spend,
        avg(t.amount)::numeric(18, 2)  as avg_spend,
        max(t.amount)::numeric(18, 2)  as max_spend
    from transactions t
    left join accounts a using (account_id)
    group by 1, 2, 3, 4, 5
)

select * from aggregated

-- models/marts/mart_daily_category_spend.sql
-- Daily spend summary by merchant category
-- Primary analytics layer for dashboarding and reporting

with transactions as (
    select * from {{ ref('stg_transactions') }}
    where transaction_type = 'DEBIT'
),

daily_summary as (
    select
        transaction_date,
        transaction_month,
        merchant_category,
        channel,
        merchant_state,

        count(*)                                as transaction_count,
        sum(amount)                             as total_spend,
        avg(amount)                             as avg_transaction_value,
        min(amount)                             as min_transaction_value,
        max(amount)                             as max_transaction_value,
        count(distinct account_id)              as unique_accounts,
        count(distinct merchant_name)           as unique_merchants

    from transactions
    group by 1, 2, 3, 4, 5
),

with_ranking as (
    select
        *,
        rank() over (
            partition by transaction_date
            order by total_spend desc
        )                                       as spend_rank_for_day,

        sum(total_spend) over (
            partition by transaction_month, merchant_category
            order by transaction_date
            rows between unbounded preceding and current row
        )                                       as cumulative_monthly_spend

    from daily_summary
)

select * from with_ranking
order by transaction_date desc, spend_rank_for_day

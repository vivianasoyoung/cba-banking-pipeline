
  
    

  create  table "cba_pipeline"."staging_marts"."mart_daily_category_spend__dbt_tmp"
  
  
    as
  
  (
    with transactions as (
    select * from "cba_pipeline"."staging_staging"."stg_transactions"
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
)

select * from daily_summary
order by transaction_date desc
  );
  
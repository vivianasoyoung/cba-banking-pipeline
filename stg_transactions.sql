-- models/staging/stg_transactions.sql
-- Cleans and standardises raw transaction data

with source as (
    select * from {{ source('raw', 'transactions') }}
),

cleaned as (
    select
        transaction_id,
        account_id,
        bsb,
        account_number,
        transaction_date::date                          as transaction_date,
        date_trunc('month', transaction_date)::date     as transaction_month,
        extract(dow from transaction_date)::int         as day_of_week,
        extract(hour from transaction_date)::int        as hour_of_day,

        -- Normalise amount: always positive, sign encoded in transaction_type
        abs(amount)                                     as amount,
        transaction_type,
        case
            when transaction_type = 'DEBIT'  then -abs(amount)
            when transaction_type = 'CREDIT' then  abs(amount)
        end                                             as signed_amount,

        upper(trim(merchant_name))                      as merchant_name,
        upper(trim(merchant_category))                  as merchant_category,
        upper(trim(merchant_state))                     as merchant_state,
        upper(trim(channel))                            as channel,
        upper(trim(status))                             as status,
        balance_after,
        description,
        loaded_at

    from source
    where
        transaction_id is not null
        and account_id is not null
        and amount > 0
        and status != 'DECLINED'   -- exclude declined txns from analytics
)

select * from cleaned

{% snapshot accounts_snapshot %}

{{
    config(
        target_schema='snapshots',
        unique_key='account_id',
        strategy='check',
        check_cols=['balance', 'credit_limit', 'account_type']
    )
}}

select * from {{ source('raw', 'accounts') }}

{% endsnapshot %}

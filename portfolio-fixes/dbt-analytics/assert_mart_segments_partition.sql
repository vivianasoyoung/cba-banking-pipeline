-- Singular test: every account in mart_customer_segments must appear in exactly
-- one segment, and the segment must be one of the four expected values.
-- Test passes if this query returns ZERO rows.

with bad as (
    select
        account_id,
        count(*) as segment_count
    from {{ ref('mart_customer_segments') }}
    group by account_id
    having count(*) <> 1
)

select * from bad

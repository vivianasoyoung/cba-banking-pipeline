
    
    

with all_values as (

    select
        transaction_type as value_field,
        count(*) as n_records

    from "cba_pipeline"."raw"."transactions"
    group by transaction_type

)

select *
from all_values
where value_field not in (
    'DEBIT','CREDIT'
)



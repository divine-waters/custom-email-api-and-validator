-- Selects all columns for all validation results stored in the local database
SELECT
    id,
    contact_id,
    mx_valid,
    is_disposable,
    is_blacklisted,
    is_free_provider,
    created_at
FROM
    validation_results
ORDER BY
    created_at DESC;

PRINT 'Selected all validation results.';

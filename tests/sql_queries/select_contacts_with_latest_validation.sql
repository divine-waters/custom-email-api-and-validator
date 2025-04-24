-- Selects contact details along with their most recent validation result

WITH LatestValidation AS (
    -- This CTE finds the latest validation record for each contact_id
    SELECT
        vr.contact_id,
        vr.email AS validated_email, -- Email used during this specific validation
        vr.domain,
        vr.mx_valid,
        vr.is_disposable,
        vr.is_blacklisted,
        vr.is_free_provider,
        vr.created_at AS validated_at,
        -- Assign a row number to each validation per contact, ordered newest first
        ROW_NUMBER() OVER(PARTITION BY vr.contact_id ORDER BY vr.created_at DESC, vr.id DESC) as rn
        -- Added vr.id DESC as a tie-breaker in case multiple validations happen in the same exact millisecond
    FROM
        validation_results vr
)
SELECT
    c.contact_id AS contact_hubspot_id,
    c.firstname,
    c.lastname,
    c.email AS contact_email, -- The primary email stored in the contacts table
    lv.validated_email,      -- The email address that was actually validated (might differ if updated)
    lv.domain,
    lv.mx_valid,
    lv.is_disposable,
    lv.is_blacklisted,
    lv.is_free_provider,
    lv.validated_at          -- Timestamp of the latest validation
FROM
    contacts c               -- Start with the contacts table
LEFT JOIN
    LatestValidation lv ON c.contact_id = lv.contact_id AND lv.rn = 1 -- Join only the latest record (rn=1)
ORDER BY
    c.contact_id; -- Or order as needed, e.g., ORDER BY lv.validated_at DESC

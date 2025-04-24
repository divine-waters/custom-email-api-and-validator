-- Selects all columns for all contacts stored in the local database
SELECT
    contact_id,
    email,
    firstname,
    lastname,
    created_at
FROM
    contacts
ORDER BY
    created_at DESC;

PRINT 'Selected all contacts.';

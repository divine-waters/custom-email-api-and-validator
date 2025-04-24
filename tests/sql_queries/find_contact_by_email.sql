-- Finds a contact by a specific email address
-- *** IMPORTANT: Replace 'user@example.com' with the actual email you are searching for ***
DECLARE @TargetEmail NVARCHAR(255) = 'garrettglick85@gmail.com';

SELECT
    contact_id,
    email,
    firstname,
    lastname,
    created_at
FROM
    contacts
WHERE
    email = @TargetEmail;

PRINT 'Search complete for email: ' + @TargetEmail;

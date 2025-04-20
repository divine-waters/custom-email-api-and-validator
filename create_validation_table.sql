-- File: create_validation_table.sql

-- Ensure we are in the correct database context
USE hubspot_contacts;
GO

-- Check if the table already exists before trying to create it (optional but safer)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[validation_results]') AND type in (N'U'))
BEGIN
    PRINT 'Creating table validation_results...';
    CREATE TABLE dbo.validation_results (
        contact_id VARCHAR(50) PRIMARY KEY, -- Assuming HubSpot IDs are strings and unique
        email VARCHAR(255) NOT NULL,
        domain VARCHAR(255),
        mx_valid BIT, -- Use BIT for boolean in SQL Server
        is_disposable BIT,
        is_blacklisted BIT,
        is_free_provider BIT,
        validation_status VARCHAR(50), -- To store 'valid', 'error', 'warning'
        validation_message NVARCHAR(MAX), -- Use NVARCHAR(MAX) for potentially long messages
        validated_at DATETIME2 DEFAULT GETDATE() -- Add a timestamp for when validation occurred
    );
    PRINT 'Table validation_results created successfully.';
END
ELSE
BEGIN
    PRINT 'Table validation_results already exists.';
END
GO

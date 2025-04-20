# utils/domain_utils.py

def extract_domain(email: str) -> str:
    """
    Extracts the domain from the email address.

    Args:
        email (str): The email address to extract the domain from.

    Returns:
        str: The domain part of the email address (e.g., "example.com").
    """
    try:
        domain = email.split('@')[-1].lower()
        return domain
    except Exception as e:
        raise ValueError(f"Invalid email address: {email}. Error: {str(e)}")

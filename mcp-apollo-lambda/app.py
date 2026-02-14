from mcpengine import MCPEngine
import os
import requests

engine = MCPEngine(name="prospector")


@engine.tool()
def find_b2b_leads(
    industry: str,
    company_size: str = "11-50",
    location: str = "Switzerland, France"
) -> str:
    """Find qualified B2B leads on Apollo.io.

    Args:
        industry: Sector (e.g. 'SaaS', 'Fintech', 'Marketing')
        company_size: Size range (11-50, 51-200, 201-500)
        location: Location (Switzerland, France, Europe)
    """
    api_key = os.getenv("APOLLO_API_KEY")
    if not api_key:
        return "ERROR: Configure APOLLO_API_KEY in Lambda Environment Variables"

    url = "https://api.apollo.io/v1/mixed_people/search"
    params = {
        "q_organization_keyword_tags": [industry],
        "organization_num_employees_ranges": [company_size],
        "person_locations": [location],
        "per_page": 10,
        "page": 1
    }
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key
    }

    try:
        response = requests.post(url, json=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("people"):
            leads = []
            for person in data["people"][:5]:
                email = person.get('email', 'N/A')
                org = person.get('organization', {})
                leads.append(
                    f"- {person['name']} | {person.get('title','N/A')} @ {org.get('name','N/A')}\n"
                    f"  Email: {email}\n"
                    f"  Website: {org.get('website_url', 'N/A')}"
                )
            return f"Found {len(data['people'])} leads:\n\n" + "\n".join(leads)
        return f"No leads found for {industry} in {location}"
    except requests.exceptions.RequestException as e:
        return f"Apollo API error: {str(e)}"
    except Exception as e:
        return f"Internal error: {str(e)}"


@engine.tool()
def find_emails_by_domain(
    domain: str,
    limit: int = 10
) -> str:
    """Find email addresses associated with a company domain using Hunter.io.

    Args:
        domain: Company domain (e.g. 'stripe.com', 'shopify.com')
        limit: Max results to return (1-100, default 10)
    """
    api_key = os.getenv("HUNTER_API_KEY")
    if not api_key:
        return "ERROR: Configure HUNTER_API_KEY in Lambda Environment Variables"

    url = "https://api.hunter.io/v2/domain-search"
    params = {
        "domain": domain,
        "api_key": api_key,
        "limit": min(limit, 100)
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json().get("data", {})

        org = data.get("organization", domain)
        pattern = data.get("pattern", "N/A")
        emails = data.get("emails", [])

        if not emails:
            return f"No emails found for {domain}"

        results = [f"Company: {org} | Email pattern: {pattern}\n"]
        for e in emails:
            name = f"{e.get('first_name','')} {e.get('last_name','')}".strip() or "N/A"
            results.append(
                f"- {name} | {e.get('position','N/A')}\n"
                f"  Email: {e['value']} (confidence: {e.get('confidence',0)}%)\n"
                f"  Department: {e.get('department','N/A')} | Seniority: {e.get('seniority','N/A')}"
            )
        return f"Found {len(emails)} emails for {domain}:\n\n" + "\n".join(results)
    except requests.exceptions.RequestException as e:
        return f"Hunter API error: {str(e)}"
    except Exception as e:
        return f"Internal error: {str(e)}"


@engine.tool()
def verify_email(email: str) -> str:
    """Verify if an email address is valid and deliverable using Hunter.io.

    Args:
        email: Email address to verify (e.g. 'john@company.com')
    """
    api_key = os.getenv("HUNTER_API_KEY")
    if not api_key:
        return "ERROR: Configure HUNTER_API_KEY in Lambda Environment Variables"

    url = "https://api.hunter.io/v2/email-verifier"
    params = {"email": email, "api_key": api_key}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json().get("data", {})

        status = data.get("status", "unknown")
        result = data.get("result", "unknown")
        score = data.get("score", 0)

        return (
            f"Email: {email}\n"
            f"Status: {status}\n"
            f"Result: {result}\n"
            f"Score: {score}/100\n"
            f"Webmail: {data.get('webmail', False)}\n"
            f"Disposable: {data.get('disposable', False)}"
        )
    except requests.exceptions.RequestException as e:
        return f"Hunter API error: {str(e)}"
    except Exception as e:
        return f"Internal error: {str(e)}"


@engine.tool()
def find_email(
    domain: str,
    first_name: str,
    last_name: str
) -> str:
    """Find a specific person's email address using Hunter.io.

    Args:
        domain: Company domain (e.g. 'google.com')
        first_name: Person's first name
        last_name: Person's last name
    """
    api_key = os.getenv("HUNTER_API_KEY")
    if not api_key:
        return "ERROR: Configure HUNTER_API_KEY in Lambda Environment Variables"

    url = "https://api.hunter.io/v2/email-finder"
    params = {
        "domain": domain,
        "first_name": first_name,
        "last_name": last_name,
        "api_key": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json().get("data", {})

        email = data.get("email")
        if not email:
            return f"No email found for {first_name} {last_name} at {domain}"

        return (
            f"Found: {email}\n"
            f"Confidence: {data.get('confidence', 0)}%\n"
            f"Name: {first_name} {last_name}\n"
            f"Domain: {domain}\n"
            f"Position: {data.get('position', 'N/A')}"
        )
    except requests.exceptions.RequestException as e:
        return f"Hunter API error: {str(e)}"
    except Exception as e:
        return f"Internal error: {str(e)}"


handler = engine.get_lambda_handler()

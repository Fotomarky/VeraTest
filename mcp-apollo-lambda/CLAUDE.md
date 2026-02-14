# MCP Prospector

MCP server deployed on AWS Lambda for B2B lead prospecting via Apollo.io and Hunter.io.

## Architecture

- **Runtime**: Python 3.12 container image on AWS Lambda
- **Region**: eu-north-1
- **ECR Repository**: `431118444797.dkr.ecr.eu-north-1.amazonaws.com/mcp-apollo`
- **Lambda Function URL**: https://j3va2xi6zyn66s6qtrgbvcbjwi0kxkap.lambda-url.eu-north-1.on.aws/
- **MCP Endpoint**: https://j3va2xi6zyn66s6qtrgbvcbjwi0kxkap.lambda-url.eu-north-1.on.aws/mcp/

## Tools

### find_b2b_leads (Apollo.io)
Find qualified B2B leads. Requires Apollo paid API plan.

- **industry** (required): Sector (e.g. "SaaS", "Fintech", "Marketing")
- **company_size** (optional, default "11-50"): Size range (11-50, 51-200, 201-500)
- **location** (optional, default "Switzerland, France"): Location filter

### find_emails_by_domain (Hunter.io)
Find email addresses associated with a company domain.

- **domain** (required): Company domain (e.g. "stripe.com")
- **limit** (optional, default 10): Max results (1-100)

### find_email (Hunter.io)
Find a specific person's email address.

- **domain** (required): Company domain (e.g. "google.com")
- **first_name** (required): Person's first name
- **last_name** (required): Person's last name

### verify_email (Hunter.io)
Verify if an email address is valid and deliverable.

- **email** (required): Email address to verify

## Environment Variables

Set in Lambda Configuration > Environment Variables:

- `APOLLO_API_KEY`: Apollo.io API key (requires paid API plan for search endpoints)
- `HUNTER_API_KEY`: Hunter.io API key (free tier: 25 searches/month)

## MCP Client Configuration

```json
{
  "mcpServers": {
    "prospector": {
      "type": "streamable-http",
      "url": "https://j3va2xi6zyn66s6qtrgbvcbjwi0kxkap.lambda-url.eu-north-1.on.aws/mcp/"
    }
  }
}
```

## Deploy

```bash
# Login to ECR
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 431118444797.dkr.ecr.eu-north-1.amazonaws.com

# Build and push
docker build --platform linux/amd64 --provenance=false -t mcp-apollo /Users/marcocaruso/mcp-apollo-lambda
docker tag mcp-apollo:latest 431118444797.dkr.ecr.eu-north-1.amazonaws.com/mcp-apollo:latest
docker push 431118444797.dkr.ecr.eu-north-1.amazonaws.com/mcp-apollo:latest

# Update Lambda
aws lambda update-function-code --function-name mcp-apollo --image-uri 431118444797.dkr.ecr.eu-north-1.amazonaws.com/mcp-apollo:latest --region eu-north-1
```

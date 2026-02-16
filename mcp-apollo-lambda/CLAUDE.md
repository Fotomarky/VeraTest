# MCP Prospector

MCP-powered lead generation and CRM automation. Three servers, one Notion DB, zero manual data entry.

## Live Stack

| Server | Status | Tools | Install |
|--------|--------|-------|---------|
| **Prospector** | LIVE | find_b2b_leads, find_emails_by_domain, find_email, verify_email | Lambda |
| **Notion** | WEEK 1 | create_lead, update_lead, query_pipeline | npx @notionhq/notion-mcp-server |
| **Gmail** | WEEK 1 | send_email, read_inbox, search_threads | GitHub Awesome MCP Gmail |

## Infrastructure

- **Lambda**: `mcp-apollo` in eu-north-1
- **MCP Endpoint**: https://j3va2xi6zyn66s6qtrgbvcbjwi0kxkap.lambda-url.eu-north-1.on.aws/mcp/
- **ECR**: `431118444797.dkr.ecr.eu-north-1.amazonaws.com/mcp-apollo`
- **Notion Lead DB**: `3074d7f5-0658-817e-b1a1-fdc80291f68d`

## Env Keys (4 total)

```
APOLLO_API_KEY    # Apollo.io (paid API plan needed)
HUNTER_API_KEY    # Hunter.io (free: 25 searches/mo)
NOTION_API_KEY    # ntn_208030285688...
GMAIL_OAUTH       # Week 1 add-on
```

## Orchestration: Lean Lead Lifecycle

Notion is the single source of truth. Every action updates the DB automatically.

```
FIND ──> ENRICH ──> ADD TO NOTION ──> OUTREACH ──> UPDATE ──> CLOSE
  |         |            |               |            |          |
Apollo   Hunter.io    Notion API      Gmail       Notion     Manual
Hunter                Status:New    Thread link   Status:     (Stripe
                      Pipeline:     auto-saved    Contacted   link)
                      Lead                        Replied
                                                  Meeting
                                                  Won/Lost
```

### Automated Status Transitions

```
Action                          Notion Status    Pipeline Stage
─────────────────────────────────────────────────────────────────
Lead found (Hunter/Apollo)   -> New              Lead
Email verified               -> New              Lead (Email Verified: true)
Outreach sent (Gmail)        -> Contacted        Lead
Reply received (Gmail)       -> Replied          Qualified
Meeting booked               -> Meeting          Negotiation
Proposal sent                -> Proposal Sent    Proposal Sent
Deal closed                  -> Won              Closed Won
No response after 3 touches  -> Cold             Lead (Priority: Cold)
```

### Week 1 Workflow: Prospector + Notion

Claude prompt: "Find 50 SaaS founders in Geneva, add to Notion"

```
1. Hunter.io -> find_emails_by_domain for target companies
2. Hunter.io -> verify_email for each contact
3. Notion API -> create lead:
   {
     Name, Email, Company, Position,
     Status: "New",
     Pipeline: "Lead",
     Source: "Hunter.io",
     Email Verified: true,
     Confidence: 83%
   }
4. Repeat for next company
```

Manual step: Email top 10 leads, then update Notion Status -> Contacted.

### Week 1 Add-On: Gmail MCP

Claude prompt: "Send personalized outreach to all Notion leads with Status: New"

```
1. Notion -> query leads WHERE Status = "New" AND Email Verified = true
2. For each lead:
   a. Gmail -> send_email (personalized by Company + Position)
   b. Notion -> update lead:
      {
        Status: "Contacted",
        Last Contacted: today,
        Next Follow-up: today + 3 days,
        Channel: "Email",
        Gmail Thread: thread_link
      }
3. Slack (optional) -> notify #sales: "10 leads contacted"
```

Claude prompt: "Check for replies and update pipeline"

```
1. Notion -> query leads WHERE Status = "Contacted"
2. For each lead:
   a. Gmail -> search_threads for lead email
   b. If reply found:
      Notion -> update: Status: "Replied", Pipeline: "Qualified", Priority: "Hot"
   c. If no reply + 3 days passed:
      Gmail -> send follow-up
      Notion -> update: Next Follow-up: today + 5 days
   d. If no reply after 3 touches:
      Notion -> update: Priority: "Cold"
```

### Week 2: Add Slack + Stripe (only after 5 customers)

```
Slack  -> auto-notify on status changes
Stripe -> payment links in proposals
Xero   -> invoice on close
```

## MCP Client Config (Target)

```json
{
  "mcpServers": {
    "prospector": {
      "type": "streamable-http",
      "url": "https://j3va2xi6zyn66s6qtrgbvcbjwi0kxkap.lambda-url.eu-north-1.on.aws/mcp/"
    },
    "notion": {
      "command": "npx",
      "args": ["-y", "@notionhq/notion-mcp-server"],
      "env": { "NOTION_API_KEY": "ntn_..." }
    },
    "gmail": {
      "command": "npx",
      "args": ["-y", "@anthropic/gmail-mcp-server"],
      "env": { "GMAIL_OAUTH": "..." }
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

## Quick Reference: Claude Prompts

```
# Prospecting
"Find emails for all real estate companies in Geneva, verify them, add to Notion"

# Outreach
"Send personalized cold email to all New leads in Notion, update status"

# Follow-up
"Check Gmail for replies from Contacted leads, update Notion pipeline"

# Pipeline review
"Show me all Hot leads in Negotiation stage with deal values"

# Weekly report
"Count leads by status and pipeline stage, list overdue follow-ups"
```

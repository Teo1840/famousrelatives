FamousRelatives is a web application that queries the FamilySearch API to compute and visualize genealogical relationships between a user and historically or culturally significant individuals.

The project focuses on highlighting how people are deeply interconnected through shared ancestry, often linking users to figures of local, regional, or historical importance rather than only globally famous personalities.

FamousRelatives requires a valid FamilySearch access token to operate.
- The token is supplied by the user
- No credentials are stored permanently
- The token is used exclusively to perform relationship queries against the FamilySearch API

Core Workflow.
- The application loads a CSV file containing multiple FamilySearch person IDs
- For each person ID:
      A relationship query is sent to the FamilySearch API
      The relationship path is parsed and normalized
- The result is transformed into a simplified genealogical tree structure
- The processed result is either:
      returned directly, or
      retrieved from cache if a valid cached version exists

To avoid excessive API usage and comply with FamilySearch rate limits, the application implements a 24-hour caching layer using MySQL.
- Each computed relationship tree is stored as JSON
- Cached entries include a creation timestamp
- If the same query is requested within 24 hours:
      the cached result is returned
      no external API request is performed
This significantly improves performance and reduces unnecessary API calls.

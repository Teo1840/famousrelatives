# FamousRelatives

A small web app that uses the FamilySearch API to compute and visualize relationship paths between a user and a curated list of historically/culturally significant people.

*Focus:* API integration, reliability patterns (timeouts/retries), caching to reduce external calls, and containerized deployment (Docker).

## Why this project
The original FamilySearch “Famous Relatives” feature is intentionally limited and subjective, with a small, non-controversial list of historically important people.

This project was created to explore an alternative approach:
allowing users to define their *own curated lists of culturally relevant figures*, with a regional or personal focus, making the experience more meaningful and engaging.

At the same time, the project was designed to practice real-world backend challenges, including:
- Working with an external API (latency, failures, rate limits)
- Reducing request volume via caching to protect upstream services
- Handling transient errors safely (timeouts, retries, clear error messages)
- Shipping a reproducible environment using Docker

The result is a product-driven idea combined with real engineering constraints.

🔐 **Authentication & Security**

- FamousRelatives requires a valid FamilySearch access token provided by the user.
- Tokens are supplied manually by the user
- No credentials or tokens are stored permanently
- Tokens are used exclusively to perform relationship queries via the FamilySearch API


⚙️ **Core Workflow**

1. The application loads a CSV file containing multiple FamilySearch person IDs
2. For each person ID:
- A relationship query is sent to the FamilySearch API
- The relationship path is parsed and normalized

3. The processed data is rendered in a web interface for visualization and analysis
4. The data is temporarely stored in a DB to reduce the amount of requests to the FamilySearch servers


🛠️ **Technologies Used**

- Python (backend logic and API interaction)
- HTML/CSS (frontend templates)
- Docker (containerized deployment – early implementation)


🚧 **Project Status**

This project is currently under active development.
Planned improvements include:
- Enhanced data visualization
- Better error handling and validation
- Expanded documentation and examples
- Improved Docker configuration


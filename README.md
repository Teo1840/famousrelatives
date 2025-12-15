FamousRelatives

FamousRelatives is a web application that uses the FamilySearch API to compute and visualize genealogical relationships between a user and historically or culturally significant individuals.

The project highlights how people are deeply interconnected through shared ancestry, often linking users to figures of local, regional, or historical importance—not only globally famous personalities.


---

✨ Key Features

Queries the FamilySearch API to compute relationship paths

Normalizes and parses genealogical relationship data

Visualizes connections between individuals in a clear, user-friendly way

Focuses on explainability and data clarity rather than raw celebrity matching



---

🔐 Authentication & Security

FamousRelatives requires a valid FamilySearch access token provided by the user.

Tokens are supplied manually by the user

No credentials or tokens are stored permanently

Tokens are used exclusively to perform relationship queries via the FamilySearch API



---

⚙️ Core Workflow

1. The application loads a CSV file containing multiple FamilySearch person IDs


2. For each person ID:

A relationship query is sent to the FamilySearch API

The relationship path is parsed and normalized



3. The processed data is rendered in a web interface for visualization and analysis




---

🛠️ Technologies Used

Python (backend logic and API interaction)

HTML/CSS (frontend templates)

Docker (containerized deployment – early implementation)

FamilySearch API



---

🚧 Project Status

This project is currently under active development.
Planned improvements include:

Enhanced data visualization

Better error handling and validation

Expanded documentation and examples

Improved Docker configuration



---

🎯 Purpose

This project was built as a practical learning exercise to strengthen skills in:

API integration

Data parsing and normalization

Backend development

Technical documentation

Working with real-world, structured data

# Dummy Charging Management System (CMS) Server

This repository contains a simple, dummy Charging Management System (CMS) server prototype. It was built using **Goose AI** to demonstrate rapid development and prototyping capabilities.

## Project Overview

The purpose of this project is to simulate the core functionalities of a CMS provider for testing and development purposes.

The implemented features include:

-   **Start Charging:** Simulate the initiation of a charging session.

-   **Stop Charging:** Simulate the termination of a charging session.

-   **List Sessions/Transactions:** View a list of recorded charging sessions or transactions.

## Built with Goose AI

This prototype was developed rapidly leveraging the integrated tools provided by Goose AI, specifically the `developer__shell` for executing commands (like installing dependencies and running the server) and the `developer__text_editor` for writing and modifying the Python code.

Use of Goose streamlined the development workflow and allowed for quick iteration and debugging, including resolving a technical challenge related to WebSocket implementation by switching frameworks from `flask-sockets` to `quart`.

## Getting Started

*(Note: Detailed setup instructions can be added here later if needed, but for this simple README, we\'ll keep it brief)*

To run this project, you would typically need Python installed. Dependencies can be installed using pip:

```bash
pip install quart websockets
```

You can then run the server script.

```bash
python server.py # Or whatever your main server file is named
```

*(Replace `server.py` with the actual name of your main server file)*

## API Examples

Here are examples demonstrating how to interact with the dummy CMS server.

*(Note: Endpoints and request/response formats are illustrative and may vary based on implementation details.)*

### Start Charging Transaction

**Request:**

```bash
# Example using curl
curl -X POST \\\
  http://localhost:5050/start_charging \\\
  -H "Content-Type: application/json" \\\
  -d \'{
        "connectorId": 1,
        "idTag": "RFID123",
        "meterStart": 0,
        "timestamp": "2023-10-27T10:00:00Z"
      }\'
```

**Expected Response (Success):**

```json
{
  "transactionId": 123,
  "idTagInfo": {
    "status": "Accepted"
  }
}
```

*(Add screenshot of request and response here)*
<!-- ![Start Transaction Example Screenshot](link/to/your/start_charging_screenshot.png) -->

### Stop Charging Transaction

**Request:**

```bash
# Example using curl
curl -X POST \\\
  http://localhost:5050/stop_charging \\\
  -H "Content-Type: application/json" \\\\\
  -d \'{
        "transactionId": 123,
        "meterStop": 1500,
        "timestamp": "2023-10-27T10:30:00Z",
        "idTag": "RFID123"
      }\'
```

**Expected Response (Success):**

```json
{
  "idTagInfo": {
    "status": "Accepted"
  },
  "meterStop": 1500,
  "timestamp": "2023-10-27T10:30:00Z",
  "transactionId": 123
}
```

*(Add screenshot of request and response here)*
<!-- ![Stop Transaction Example Screenshot](link/to/your/stop_charging_screenshot.png) -->

### List All Sessions/Transactions

**Request:**

```bash
# Example using curl
curl -X GET \\\
  http://localhost:5050/sessions
```

**Expected Response (Success):**

```json
[
  {
    "transactionId": 123,
    "connectorId": 1,
    "idTag": "RFID123",
    "meterStart": 0,
    "timestampStart": "2023-10-27T10:00:00Z",
    "meterStop": 1500,
    "timestampStop": "2023-10-27T10:30:00Z"
  },
  {
    "transactionId": 124,
    "connectorId": 2,
    "idTag": "RFID456",
    "meterStart": 500,
    "timestampStart": "2023-10-27T11:00:00Z",
    "meterStop": null,
    "timestampStop": null
  }
]
```

*(Add screenshot of request and response here)*
<!-- ![Sessions Example Screenshot](link/to/your/sessions_screenshot.png) -->

## License

[Include license information here if applicable]

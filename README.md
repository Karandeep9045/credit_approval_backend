# Credit Approval Backend System

A sophisticated Django REST API system for managing customer credit applications and loan approvals with intelligent credit scoring and background data processing.

## 🏗️ System Architecture

### Core Components

- **Django REST Framework**: API endpoints and serialization
- **PostgreSQL**: Primary database for customer and loan data
- **Celery + Redis**: Background task processing for data ingestion
- **Credit Scoring Engine**: Intelligent loan approval algorithm
- **Excel Data Ingestion**: Automated import from Excel files

### Key Features

- ✅ Customer registration with automated credit limit calculation
- ✅ Intelligent credit scoring based on loan history
- ✅ Loan enterest rate correction
- ✅ Automated loan creation and management
- ✅ Comprehensive loan viewing and tracking
- ✅ Background data ingestion from Excel files
- ✅ RESTful API with proper error handling

## 📋 Requirements

- **Docker Engine** must be running before you execute any Docker commands.
- Docker Compose (usually included with Docker Desktop)

## 🚀 Quick Start with Docker

### 1. Clone the Repository

```bash
git clone <repository-url>
cd credit_approval_backend
```

### 2. Build and Run the Application

**Make sure Docker Engine is running before executing the following command:**

```bashligibility checking with i
docker compose up --build
```

- The Django app will be available at [http://localhost:8000](http://localhost:8000)
- The PostgreSQL database and all migrations will be handled automatically.
- Data persistence is managed via Docker volumes.

### 3. Stopping the Application

To stop all running containers:

```bash
docker compose down
```

---

**Note:**  
- All environment variables and database credentials are pre-configured in the `docker-compose.yml` and `credit_system/settings.py`.
- For custom configuration, edit these files as needed.

---

## 📬 Sample API Requests

You can use [Postman](https://www.postman.com/) or `curl` to test the API endpoints.  
Below are sample requests for each endpoint:

**Base URL** `http://127.0.0.1:8000`

### 1. Register a New Customer

**POST** `/api/register`

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "9876543210",
  "monthly_income": 75000,
  "age": 28
}
```

### 2. Check Loan Eligibility

**POST** `/api/check-eligibility`

```json
{
  "customer_id": 3,
  "loan_amount": 200000,
  "interest_rate": 10.0,
  "tenure": 24
}
```

### 3. Create a New Loan

**POST** `/api/create-loan`

```json
{
  "customer_id": 3,
  "loan_amount": 200000,
  "interest_rate": 10.0,
  "tenure": 24
}
```

### 4. View Loan Details

**GET** `/api/view-loan/<loan_id>`

Example:
```
GET /api/view-loan/3050
```

### 5. View All Loans for a Customer

**GET** `/api/view-loans/<customer_id>`

Example:
```
GET /api/view-loans/3
```

---

**Once the application is running, you can access the API documentation and test endpoints at [http://localhost:8000](http://localhost:8000).**
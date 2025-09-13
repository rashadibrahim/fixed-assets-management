# Fixed Assets Management API

A Flask-based API for managing fixed assets, warehouses, and branches.

## Features

- RESTful API for managing fixed assets, warehouses, and branches
- File upload support for asset attachments
- Swagger documentation for easy API exploration
- PostgreSQL database for improved performance and scalability

## API Documentation

This project includes Swagger documentation to help you explore and test the API endpoints.

### Accessing Swagger UI

When the application is running, you can access the Swagger UI at:

```
http://localhost:5000/api/docs
```

The Swagger UI provides:

- Interactive documentation for all API endpoints
- Request/response schemas for each endpoint
- The ability to test API calls directly from the browser
- Detailed parameter descriptions

### API Namespaces

The API is organized into the following namespaces:

1. **Branches** (`/branches`)
   - Create, read, update, and delete branch information
   - View warehouses associated with a branch

2. **Warehouses** (`/warehouses`)
   - Create, read, update, and delete warehouse information
   - Filter warehouses by branch

3. **Fixed Assets** (`/assets`)
   - Create, read, update, and delete fixed asset information
   - Upload and download asset attachments
   - Filter assets by warehouse

## Running the Application

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up PostgreSQL database:
   - Install PostgreSQL if not already installed
   - Create a database named `fixed_assets`
   - Update connection details in `config.py` if needed

3. Migrate data (if coming from SQLite):
   ```bash
   python migrate_to_postgres.py
   ```

4. Run the application:
   ```bash
   flask run
   ```

5. Access the API at `http://localhost:5000/api`

## Database Configuration

The application uses PostgreSQL for improved performance and scalability. See [POSTGRES_MIGRATION.md](POSTGRES_MIGRATION.md) for detailed setup and migration instructions.
   pip install -r requirements.txt
   ```

2. Run the Flask application:
   ```
   flask run
   ```

3. Access the Swagger UI at http://localhost:5000/api/docs